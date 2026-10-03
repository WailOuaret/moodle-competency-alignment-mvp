<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Moodle is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Moodle.  If not, see <http://www.gnu.org/licenses/>.

namespace local_compalign\service;

/**
 * Validates the alignment service's answer against what Moodle sent, before anything is stored.
 *
 * The service is trusted to run the research engine, not to be correct about Moodle. So the
 * answer is checked as untrusted input: its shape, the resource it names, that every proposed
 * competency is one Moodle sent, and that every quotation really occurs in the text Moodle sent.
 * A failed check rejects the whole answer, so nothing partial is ever stored or shown.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class response_validator {
    /** Most evidence quotations accepted for one suggestion. */
    private const MAX_EVIDENCE = 20;
    /** Longest evidence quotation accepted. */
    private const MAX_QUOTE_CHARS = 4000;
    /** Most hierarchy warnings accepted for one suggestion. */
    private const MAX_WARNINGS = 10;
    /** Most diagnostics accepted for one analysis. */
    private const MAX_DIAGNOSTICS = 50;
    /** Longest message accepted anywhere in the answer. */
    private const MAX_MESSAGE_CHARS = 500;
    /** Most problems reported for one rejected answer. */
    private const MAX_PROBLEMS = 10;

    /** Allowed shape of a code: warning type, diagnostic code. */
    private const CODE_PATTERN = '/^[a-z][a-z0-9_]{0,59}$/';

    /** @var string[] Problems found so far. */
    private array $problems = [];

    /**
     * Validate an answer.
     *
     * @param array $response The decoded JSON answer.
     * @param string $resourceid The resource id Moodle sent.
     * @param string[] $idnumbers The competency idnumbers Moodle sent.
     * @param int $topk The Top-K Moodle requested.
     * @param int $maxsuggestions The most suggestions Moodle asked for.
     * @param string $resourcetext The resource text Moodle sent.
     * @return array The validated analysis: analysisid, backend, model, completeness, abstained,
     *         manifest, suggestions and diagnostics.
     * @throws analysis_exception With code invalid_response when any check fails.
     */
    public static function validate(
        array $response,
        string $resourceid,
        array $idnumbers,
        int $topk,
        int $maxsuggestions,
        string $resourcetext
    ): array {
        $validator = new self();

        return $validator->run($response, $resourceid, $idnumbers, $topk, $maxsuggestions, $resourcetext);
    }

    /**
     * Normalise text the way the service does before it compares or quotes it.
     *
     * HTML entities are decoded, compatibility characters are folded (NFKC) and whitespace is
     * collapsed. Both the resource text and each quotation go through this before the check.
     *
     * @param string $text Any text.
     * @return string The normalised text.
     */
    public static function normalise_for_comparison(string $text): string {
        $text = html_entity_decode($text, ENT_QUOTES | ENT_HTML5, 'UTF-8');

        if (class_exists(\Normalizer::class)) {
            $folded = \Normalizer::normalize($text, \Normalizer::FORM_KC);
            $text = is_string($folded) ? $folded : $text;
        }

        return trim((string) preg_replace('/\s+/u', ' ', $text));
    }

    /**
     * Run every check.
     *
     * @param array $response The decoded JSON answer.
     * @param string $resourceid The resource id Moodle sent.
     * @param string[] $idnumbers The competency idnumbers Moodle sent.
     * @param int $topk The Top-K Moodle requested.
     * @param int $maxsuggestions The most suggestions Moodle asked for.
     * @param string $resourcetext The resource text Moodle sent.
     * @return array The validated analysis.
     */
    private function run(
        array $response,
        string $resourceid,
        array $idnumbers,
        int $topk,
        int $maxsuggestions,
        string $resourcetext
    ): array {
        $known = array_fill_keys($idnumbers, true);

        if (($response['schema_version'] ?? null) !== alignment_client::SCHEMA_VERSION) {
            $this->problems[] = 'schema_version is not ' . alignment_client::SCHEMA_VERSION;
        }

        $analysisid = $response['analysis_id'] ?? null;
        if (!is_string($analysisid) || !preg_match('/^[A-Za-z0-9_.-]{1,64}$/', $analysisid)) {
            $this->problems[] = 'analysis_id is missing or malformed';
        }

        if (($response['status'] ?? null) !== 'completed') {
            $this->problems[] = 'status is not completed';
        }

        if (($response['resource_id'] ?? null) !== $resourceid) {
            $this->problems[] = 'resource_id does not match the resource that was sent';
        }

        $abstained = $response['abstained'] ?? null;
        if (!is_bool($abstained)) {
            $this->problems[] = 'abstained is not a boolean';
        }

        $manifest = $this->manifest($response['manifest'] ?? null, $topk);
        $suggestions = $this->suggestions(
            $response['suggestions'] ?? null,
            $known,
            $topk,
            $maxsuggestions,
            self::normalise_for_comparison($resourcetext)
        );
        $diagnostics = $this->diagnostics($response['diagnostics'] ?? null);

        // Compare with what the service sent: a suggestion dropped above must not also look like an abstention.
        $offered = is_array($response['suggestions'] ?? null) ? $response['suggestions'] : [];
        if (is_bool($abstained) && $abstained !== ($offered === [])) {
            $this->problems[] = 'abstained disagrees with the suggestions';
        }

        if ($this->problems) {
            throw new analysis_exception(
                'invalid_response',
                'The response from the alignment service failed validation.',
                array_slice($this->problems, 0, self::MAX_PROBLEMS)
            );
        }

        return [
            'analysisid' => $analysisid,
            'backend' => $manifest['backend'],
            'model' => $manifest['model'],
            'completeness' => $manifest['completeness'],
            'abstained' => $abstained,
            'manifest' => $manifest,
            'suggestions' => $suggestions,
            'diagnostics' => $diagnostics,
        ];
    }

    /**
     * Validate the manifest.
     *
     * @param mixed $manifest The manifest as decoded.
     * @param int $topk The Top-K that was requested.
     * @return array The validated manifest. Meaningless when problems were recorded.
     */
    private function manifest(mixed $manifest, int $topk): array {
        if (!is_array($manifest)) {
            $this->problems[] = 'manifest is missing';
            return ['backend' => '', 'model' => '', 'completeness' => ''];
        }

        $validated = [
            'backend' => $this->text($manifest['backend'] ?? null, 'manifest.backend', 40),
            'model' => $this->text($manifest['model'] ?? null, 'manifest.model', 100),
            'prompt_version' => $this->text($manifest['prompt_version'] ?? null, 'manifest.prompt_version', 40),
            'top_k' => $this->integer($manifest['top_k'] ?? null, 'manifest.top_k', 1, 50),
            'max_selections_per_fragment' => $this->integer(
                $manifest['max_selections_per_fragment'] ?? null,
                'manifest.max_selections_per_fragment',
                1,
                20
            ),
            'competency_catalogue_hash' => $this->text(
                $manifest['competency_catalogue_hash'] ?? null,
                'manifest.competency_catalogue_hash',
                100
            ),
            'resource_hash' => $this->text($manifest['resource_hash'] ?? null, 'manifest.resource_hash', 100),
            'fragment_count' => $this->integer($manifest['fragment_count'] ?? null, 'manifest.fragment_count', 1, 10000),
            'completeness' => $manifest['completeness'] ?? null,
            'analysed_at' => $this->text($manifest['analysed_at'] ?? null, 'manifest.analysed_at', 40),
            'duration_ms' => $this->integer($manifest['duration_ms'] ?? null, 'manifest.duration_ms', 0, PHP_INT_MAX),
        ];

        if ($validated['top_k'] !== $topk) {
            $this->problems[] = 'manifest.top_k is not the Top-K that was requested';
        }

        if (!in_array($validated['completeness'], ['complete', 'partial'], true)) {
            $this->problems[] = 'manifest.completeness is not complete or partial';
            $validated['completeness'] = '';
        }

        return $validated;
    }

    /**
     * Validate the suggestions.
     *
     * @param mixed $suggestions The suggestions as decoded.
     * @param array<string, bool> $known The idnumbers Moodle sent, as keys.
     * @param int $topk The Top-K that was requested.
     * @param int $maxsuggestions The most suggestions Moodle asked for.
     * @param string $normalisedtext The resource text, normalised for comparison.
     * @return array[] The validated suggestions.
     */
    private function suggestions(
        mixed $suggestions,
        array $known,
        int $topk,
        int $maxsuggestions,
        string $normalisedtext
    ): array {
        if (!is_array($suggestions) || !array_is_list($suggestions)) {
            $this->problems[] = 'suggestions is not a list';
            return [];
        }

        if (count($suggestions) > $maxsuggestions) {
            $this->problems[] = 'more suggestions than were asked for';
            return [];
        }

        $validated = [];
        $seen = [];

        foreach ($suggestions as $index => $suggestion) {
            $where = "suggestions[$index]";

            if (!is_array($suggestion)) {
                $this->problems[] = "$where is not an object";
                continue;
            }

            $idnumber = $suggestion['competency_idnumber'] ?? null;
            if (!is_string($idnumber) || !isset($known[$idnumber])) {
                $this->problems[] = "$where names a competency that was not sent";
                continue;
            }

            if (isset($seen[$idnumber])) {
                $this->problems[] = "$where repeats a competency";
                continue;
            }

            $seen[$idnumber] = true;
            $validated[] = [
                'idnumber' => $idnumber,
                'confidence' => $this->confidence($suggestion['confidence'] ?? null, $where),
                'bm25rank' => $this->optional_integer($suggestion['bm25_rank'] ?? null, "$where.bm25_rank", 1, $topk),
                'supportcount' => $this->integer($suggestion['support_count'] ?? null, "$where.support_count", 1, 10000),
                'evidence' => $this->evidence($suggestion['evidence'] ?? null, $where, $normalisedtext),
                'warnings' => $this->warnings($suggestion['warnings'] ?? null, $where, $known),
            ];
        }

        return $validated;
    }

    /**
     * Validate the evidence of one suggestion, including that every quotation is in the text.
     *
     * @param mixed $evidence The evidence as decoded.
     * @param string $where Where the evidence sits, for problem messages.
     * @param string $normalisedtext The resource text, normalised for comparison.
     * @return array[] The validated evidence, in the order given.
     */
    private function evidence(mixed $evidence, string $where, string $normalisedtext): array {
        if (!is_array($evidence) || !array_is_list($evidence) || !$evidence || count($evidence) > self::MAX_EVIDENCE) {
            $this->problems[] = "$where.evidence is not a list of one to " . self::MAX_EVIDENCE . ' items';
            return [];
        }

        $validated = [];
        foreach ($evidence as $position => $item) {
            $fragmentid = is_array($item) ? ($item['fragment_id'] ?? null) : null;
            $quote = is_array($item) ? ($item['quote'] ?? null) : null;

            if (!is_string($fragmentid) || $fragmentid === '' || strlen($fragmentid) > 255) {
                $this->problems[] = "$where.evidence[$position] has no valid fragment_id";
                continue;
            }

            if (!is_string($quote) || trim($quote) === '' || mb_strlen($quote) > self::MAX_QUOTE_CHARS) {
                $this->problems[] = "$where.evidence[$position] has no valid quote";
                continue;
            }

            $needle = self::normalise_for_comparison($quote);
            if ($needle === '' || !str_contains($normalisedtext, $needle)) {
                $this->problems[] = "$where.evidence[$position] is not an exact quotation of the resource";
                continue;
            }

            $validated[] = ['fragmentid' => $fragmentid, 'quote' => $quote];
        }

        return $validated;
    }

    /**
     * Validate the hierarchy warnings of one suggestion.
     *
     * @param mixed $warnings The warnings as decoded.
     * @param string $where Where the warnings sit, for problem messages.
     * @param array<string, bool> $known The idnumbers Moodle sent, as keys.
     * @return array[] The validated warnings.
     */
    private function warnings(mixed $warnings, string $where, array $known): array {
        if (!is_array($warnings) || !array_is_list($warnings) || count($warnings) > self::MAX_WARNINGS) {
            $this->problems[] = "$where.warnings is not a short list";
            return [];
        }

        $validated = [];
        foreach ($warnings as $position => $warning) {
            $code = is_array($warning) ? ($warning['code'] ?? null) : null;
            $role = is_array($warning) ? ($warning['role'] ?? null) : null;
            $related = is_array($warning) ? ($warning['related_idnumber'] ?? null) : null;
            $message = is_array($warning) ? ($warning['message'] ?? null) : null;

            $valid = is_string($code) && preg_match(self::CODE_PATTERN, $code)
                && ($role === null || in_array($role, ['parent', 'child'], true))
                && ($related === null || (is_string($related) && isset($known[$related])))
                && is_string($message) && mb_strlen($message) <= self::MAX_MESSAGE_CHARS;

            if (!$valid) {
                $this->problems[] = "$where.warnings[$position] is malformed";
                continue;
            }

            $validated[] = ['code' => $code, 'role' => $role, 'related' => $related, 'message' => $message];
        }

        return $validated;
    }

    /**
     * Validate the diagnostics.
     *
     * @param mixed $diagnostics The diagnostics as decoded.
     * @return array[] The validated diagnostics.
     */
    private function diagnostics(mixed $diagnostics): array {
        if (!is_array($diagnostics) || !array_is_list($diagnostics) || count($diagnostics) > self::MAX_DIAGNOSTICS) {
            $this->problems[] = 'diagnostics is not a list';
            return [];
        }

        $validated = [];
        foreach ($diagnostics as $position => $item) {
            $code = is_array($item) ? ($item['code'] ?? null) : null;
            $message = is_array($item) ? ($item['message'] ?? null) : null;
            $fragmentid = is_array($item) ? ($item['fragment_id'] ?? null) : null;
            $details = is_array($item) ? ($item['details'] ?? []) : null;

            $valid = is_string($code) && preg_match(self::CODE_PATTERN, $code)
                && is_string($message) && mb_strlen($message) <= self::MAX_MESSAGE_CHARS
                && ($fragmentid === null || (is_string($fragmentid) && strlen($fragmentid) <= 255))
                && is_array($details) && array_is_list($details) && count($details) <= 10
                && count(array_filter($details, 'is_string')) === count($details);

            if (!$valid) {
                $this->problems[] = "diagnostics[$position] is malformed";
                continue;
            }

            $validated[] = [
                'code' => $code,
                'message' => $message,
                'fragmentid' => $fragmentid,
                'details' => array_map(static fn(string $d): string => mb_substr($d, 0, 300), $details),
            ];
        }

        return $validated;
    }

    /**
     * A bounded string.
     *
     * @param mixed $value The value.
     * @param string $where Where the value sits, for problem messages.
     * @param int $maxlength Longest accepted length.
     * @return string The string, or an empty string when invalid.
     */
    private function text(mixed $value, string $where, int $maxlength): string {
        if (is_string($value) && $value !== '' && mb_strlen($value) <= $maxlength) {
            return $value;
        }

        $this->problems[] = "$where is missing or too long";

        return '';
    }

    /**
     * A bounded integer.
     *
     * @param mixed $value The value.
     * @param string $where Where the value sits, for problem messages.
     * @param int $min Smallest accepted value.
     * @param int $max Largest accepted value.
     * @return int The integer, or 0 when invalid.
     */
    private function integer(mixed $value, string $where, int $min, int $max): int {
        if (is_int($value) && $value >= $min && $value <= $max) {
            return $value;
        }

        $this->problems[] = "$where is not an integer from $min to $max";

        return 0;
    }

    /**
     * A bounded integer that may be absent.
     *
     * @param mixed $value The value.
     * @param string $where Where the value sits, for problem messages.
     * @param int $min Smallest accepted value.
     * @param int $max Largest accepted value.
     * @return int|null The integer, null when absent, and null when invalid.
     */
    private function optional_integer(mixed $value, string $where, int $min, int $max): ?int {
        return $value === null ? null : $this->integer($value, $where, $min, $max);
    }

    /**
     * The model confidence, which may be absent.
     *
     * @param mixed $value The value.
     * @param string $where Where the value sits, for problem messages.
     * @return float|null The confidence from 0 to 1, or null when absent or invalid.
     */
    private function confidence(mixed $value, string $where): ?float {
        if ($value === null) {
            return null;
        }

        if ((is_int($value) || is_float($value)) && is_finite((float) $value) && $value >= 0 && $value <= 1) {
            return (float) $value;
        }

        $this->problems[] = "$where.confidence is not a number from 0 to 1";

        return null;
    }
}
