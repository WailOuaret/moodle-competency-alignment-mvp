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

use local_compalign\event\analysis_requested;
use local_compalign\task\analyse_resource;

/**
 * Requests, runs and stores analyses.
 *
 * Requesting an analysis never calls the service: it records the request and queues a
 * background task. The task calls the service, validates the answer, and stores the
 * suggestions in one transaction. If anything fails the analysis is marked failed with a
 * stable error code and no suggestion is stored, so a teacher never sees a partial result.
 * The model's original suggestions are written once and never changed by a review.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
final class analysis_manager {
    /** The analysis is waiting for the background task. */
    public const STATUS_QUEUED = 'queued';
    /** The background task is calling the service. */
    public const STATUS_RUNNING = 'running';
    /** The suggestions are stored. */
    public const STATUS_COMPLETED = 'completed';
    /** The analysis failed. The error code says why. */
    public const STATUS_FAILED = 'failed';

    /** A new analysis was queued. */
    public const OUTCOME_QUEUED = 'queued';
    /** An analysis is already waiting or running for this resource, so no second one was queued. */
    public const OUTCOME_ACTIVE = 'active';
    /** An identical completed analysis exists, so the teacher can reuse it. */
    public const OUTCOME_REUSED = 'reused';

    /** The Page was edited after the analysis. */
    public const CHANGE_PAGE = 'page';
    /** The competency framework was changed, or another one was selected, after the analysis. */
    public const CHANGE_FRAMEWORK = 'framework';

    /** Seconds to wait for the lock that stops two requests creating two analyses. */
    private const LOCK_TIMEOUT = 10;
    /** Largest number of suggestions the plugin may ask for. */
    private const MAX_SUGGESTIONS_LIMIT = 10;
    /** Longest error message stored. */
    private const MAX_ERROR_MESSAGE_CHARS = 255;

    /** @var \Closure Builds the client used to talk to the service. */
    private \Closure $clientfactory;

    /**
     * Constructor.
     *
     * @param \Closure|null $clientfactory Returns an alignment_client. Defaults to one built from the plugin settings.
     */
    public function __construct(?\Closure $clientfactory = null) {
        $this->clientfactory = $clientfactory ?? static fn(): alignment_client => alignment_client::from_config();
    }

    /**
     * Ask for suggestions for a resource.
     *
     * The caller has already checked that the user may analyse the resource. Nothing here talks
     * to the service: the work is queued.
     *
     * @param \cm_info $cm The resource.
     * @param int $userid The teacher asking. The background task runs as this user.
     * @param bool $force Analyse again even when an identical completed analysis exists.
     * @param string $resourceid Which item inside the activity. Empty when there is only one.
     * @return array{analysis: \stdClass, outcome: string} The analysis and what happened.
     * @throws analysis_exception When the resource or the framework cannot be used, or the plugin is not configured.
     */
    public function request_analysis(\cm_info $cm, int $userid, bool $force = false, string $resourceid = ''): array {
        global $DB;

        // Fail early, and visibly, when nothing could possibly run. This makes no network call.
        try {
            ($this->clientfactory)();
        } catch (service_exception $exception) {
            throw new analysis_exception($exception->get_error_code(), $exception->getMessage());
        }

        $extracted = (new resource_extractor())->extract($cm, $resourceid);
        $resourceid = $extracted['resource']['resource_id'];
        $catalogue = (new competency_catalogue())->build();
        $maxsuggestions = self::configured_max_suggestions();
        $topk = alignment_client::SUPPORTED_TOP_K;

        $lock = \core\lock\lock_config::get_lock_factory('local_compalign')
            ->get_lock('request_' . $cm->id . '_' . substr(sha1($resourceid), 0, 12), self::LOCK_TIMEOUT);
        if (!$lock) {
            throw new analysis_exception('busy');
        }

        try {
            $active = $this->find_active((int) $cm->id, $resourceid);
            if ($active) {
                return ['analysis' => $active, 'outcome' => self::OUTCOME_ACTIVE];
            }

            if (!$force) {
                $reusable = $this->find_reusable(
                    (int) $cm->id,
                    $resourceid,
                    $extracted['hash'],
                    $catalogue->hash,
                    $catalogue->frameworkid,
                    $topk,
                    $maxsuggestions
                );
                if ($reusable) {
                    return ['analysis' => $reusable, 'outcome' => self::OUTCOME_REUSED];
                }
            }

            $record = (object) [
                'courseid' => (int) $cm->course,
                'cmid' => (int) $cm->id,
                'resourceid' => $extracted['resource']['resource_id'],
                'sourceitemid' => $extracted['resource']['resource_id'],
                'extractorversion' => $extracted['resource']['extractor_version'] ?? '',
                'provenance' => json_encode($extracted['provenance'] ?? [], JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR),
                'resourcetype' => $extracted['resource']['resource_type'],
                'resourcehash' => $extracted['hash'],
                'cataloguehash' => $catalogue->hash,
                'frameworkid' => $catalogue->frameworkid,
                'status' => self::STATUS_QUEUED,
                'requestedby' => $userid,
                'topk' => $topk,
                'maxsuggestions' => $maxsuggestions,
                'requestid' => 'compalign-' . bin2hex(random_bytes(8)),
                'timecreated' => time(),
            ];
            $record->id = $DB->insert_record('local_compalign_analysis', $record);

            \core\task\manager::queue_adhoc_task(analyse_resource::instance((int) $record->id, $userid), true);

            analysis_requested::create([
                'context' => \context_module::instance($cm->id),
                'objectid' => $record->id,
                'other' => ['resourceid' => $record->resourceid, 'reanalysis' => $force],
            ])->trigger();

            return ['analysis' => $record, 'outcome' => self::OUTCOME_QUEUED];
        } finally {
            $lock->release();
        }
    }

    /**
     * Say whether an item would be reused or would call the model, without queueing it.
     *
     * @param \cm_info $cm The activity.
     * @param string $resourceid The item id from the dashboard.
     * @return string active, reused or new.
     */
    public function preview_analysis(\cm_info $cm, string $resourceid): string {
        ($this->clientfactory)();
        $extracted = (new resource_extractor())->extract($cm, $resourceid);
        $resourceid = $extracted['resource']['resource_id'];
        if ($this->find_active((int) $cm->id, $resourceid)) {
            return self::OUTCOME_ACTIVE;
        }

        $catalogue = (new competency_catalogue())->build();
        $reusable = $this->find_reusable(
            (int) $cm->id,
            $resourceid,
            $extracted['hash'],
            $catalogue->hash,
            $catalogue->frameworkid,
            alignment_client::SUPPORTED_TOP_K,
            self::configured_max_suggestions()
        );

        return $reusable ? self::OUTCOME_REUSED : 'new';
    }

    /**
     * Run a queued analysis: call the service, validate the answer and store the suggestions.
     *
     * Called by the background task. It never throws: any failure is recorded on the analysis.
     *
     * @param int $analysisid The analysis.
     */
    public function run(int $analysisid): void {
        global $DB;

        $analysis = $DB->get_record('local_compalign_analysis', ['id' => $analysisid]);
        if (!$analysis || $analysis->status !== self::STATUS_QUEUED) {
            return;
        }

        $analysis->status = self::STATUS_RUNNING;
        $analysis->timestarted = time();
        $DB->update_record('local_compalign_analysis', $analysis);

        try {
            $this->execute($analysis);
        } catch (analysis_exception $exception) {
            $this->fail($analysis, $exception->get_error_code(), $exception->getMessage(), $exception->get_details());
        } catch (service_exception $exception) {
            $this->fail($analysis, $exception->get_error_code(), $exception->getMessage());
        } catch (\Throwable $exception) {
            // The message of an unexpected error is not stored: it could describe anything.
            mtrace('local_compalign: analysis ' . $analysisid . ' failed unexpectedly (' . get_class($exception) . ').');
            $this->fail($analysis, 'internal_error', 'Unexpected ' . get_class($exception) . '.');
        }
    }

    /**
     * The most recent analysis of a resource, whatever its state.
     *
     * @param int $cmid The course module.
     * @return \stdClass|null
     */
    public function get_latest(int $cmid, string $resourceid = ''): ?\stdClass {
        global $DB;

        $conditions = ['cmid' => $cmid];
        if ($resourceid !== '') {
            $conditions['resourceid'] = $resourceid;
        }
        $records = $DB->get_records('local_compalign_analysis', $conditions, 'id DESC', '*', 0, 1);

        return $records ? reset($records) : null;
    }

    /**
     * What has changed in Moodle since a completed analysis was made.
     *
     * Every quotation was checked against the Page when the answer arrived, so it was exact then. If
     * the Page has been edited since, it may not be any more, and if the framework changed, the
     * suggestions were made against other competencies. The analysis itself is left as it was stored:
     * the teacher is only told, and can analyse again.
     *
     * @param \stdClass $analysis A completed analysis.
     * @param \cm_info $cm Its resource.
     * @param catalogue_snapshot|null $catalogue The analysis' framework as it is now, or null when it cannot be read.
     * @return string[] CHANGE_PAGE and CHANGE_FRAMEWORK, for whatever differs.
     */
    public function find_changes(\stdClass $analysis, \cm_info $cm, ?catalogue_snapshot $catalogue): array {
        $changes = [];

        try {
            $extracted = (new resource_extractor())->extract($cm, (string) $analysis->resourceid);
            if (!hash_equals((string) $analysis->resourcehash, $extracted['hash'])) {
                $changes[] = self::CHANGE_PAGE;
            }
        } catch (analysis_exception) {
            // The Page can no longer be read as it was: it is empty, too long, removed or hidden from this user.
            $changes[] = self::CHANGE_PAGE;
        }

        // A framework that cannot be read is reported on its own, so it is not repeated here.
        $moved = (int) get_config('local_compalign', 'frameworkid') !== (int) $analysis->frameworkid;
        if ($moved || ($catalogue !== null && !hash_equals((string) $analysis->cataloguehash, $catalogue->hash))) {
            $changes[] = self::CHANGE_FRAMEWORK;
        }

        return $changes;
    }

    /**
     * The stored suggestions of an analysis, with their evidence and warnings.
     *
     * @param int $analysisid The analysis.
     * @return \stdClass[] In the order the service returned them. Each has evidence (list of
     *         quotation records) and warningslist (decoded warnings) added.
     */
    public function get_suggestions(int $analysisid): array {
        global $DB;

        $suggestions = $DB->get_records('local_compalign_sugg', ['analysisid' => $analysisid], 'sortorder ASC, id ASC');
        if (!$suggestions) {
            return [];
        }

        [$sql, $params] = $DB->get_in_or_equal(array_keys($suggestions));
        $evidence = [];
        $rows = $DB->get_records_select('local_compalign_evidence', "suggestionid $sql", $params, 'evidenceorder ASC, id ASC');
        foreach ($rows as $row) {
            $evidence[(int) $row->suggestionid][] = $row;
        }

        foreach ($suggestions as $suggestion) {
            $suggestion->evidence = $evidence[(int) $suggestion->id] ?? [];
            $decoded = json_decode((string) $suggestion->warnings, true);
            $suggestion->warningslist = is_array($decoded) ? $decoded : [];
        }

        return $suggestions;
    }

    /**
     * An analysis that is waiting or running for a resource.
     *
     * @param int $cmid The course module.
     * @return \stdClass|null
     */
    public function find_active(int $cmid, string $resourceid = ''): ?\stdClass {
        global $DB;

        [$sql, $params] = $DB->get_in_or_equal([self::STATUS_QUEUED, self::STATUS_RUNNING], SQL_PARAMS_NAMED, 'status');
        $where = "cmid = :cmid AND status $sql";
        $params['cmid'] = $cmid;
        if ($resourceid !== '') {
            $where .= ' AND resourceid = :resourceid';
            $params['resourceid'] = $resourceid;
        }
        $records = $DB->get_records_select(
            'local_compalign_analysis',
            $where,
            $params,
            'id DESC',
            '*',
            0,
            1
        );

        return $records ? reset($records) : null;
    }

    /**
     * A completed analysis of exactly the same content, catalogue and settings.
     *
     * @param int $cmid The course module.
     * @param string $resourcehash Digest of the resource content.
     * @param string $cataloguehash Digest of the catalogue.
     * @param int $frameworkid The framework.
     * @param int $topk The Top-K.
     * @param int $maxsuggestions The most suggestions asked for.
     * @return \stdClass|null The most recent matching analysis.
     */
    public function find_reusable(
        int $cmid,
        string $resourceid,
        string $resourcehash,
        string $cataloguehash,
        int $frameworkid,
        int $topk,
        int $maxsuggestions
    ): ?\stdClass {
        global $DB;

        $records = $DB->get_records_select(
            'local_compalign_analysis',
            'cmid = :cmid AND resourceid = :resourceid AND status = :status AND resourcehash = :resourcehash '
                . 'AND cataloguehash = :cataloguehash AND frameworkid = :frameworkid AND topk = :topk '
                . 'AND maxsuggestions = :maxsuggestions',
            [
                'cmid' => $cmid,
                'resourceid' => $resourceid,
                'status' => self::STATUS_COMPLETED,
                'resourcehash' => $resourcehash,
                'cataloguehash' => $cataloguehash,
                'frameworkid' => $frameworkid,
                'topk' => $topk,
                'maxsuggestions' => $maxsuggestions,
            ],
            'timecompleted DESC, id DESC',
            '*',
            0,
            1
        );

        return $records ? reset($records) : null;
    }

    /**
     * The configured number of suggestions, kept inside the supported range.
     *
     * @return int
     */
    public static function configured_max_suggestions(): int {
        $configured = (int) get_config('local_compalign', 'maxsuggestions');

        return $configured > 0 ? min($configured, self::MAX_SUGGESTIONS_LIMIT) : 3;
    }

    /**
     * Read the resource and the catalogue, call the service and store a validated answer.
     *
     * @param \stdClass $analysis The running analysis.
     * @throws analysis_exception|service_exception When any step fails.
     */
    private function execute(\stdClass $analysis): void {
        try {
            $cm = get_fast_modinfo((int) $analysis->courseid)->get_cm((int) $analysis->cmid);
        } catch (\moodle_exception $exception) {
            throw new analysis_exception('resource_missing', 'The resource no longer exists.', [], $exception);
        }

        $extracted = (new resource_extractor())->extract($cm, (string) $analysis->resourceid);
        $catalogue = (new competency_catalogue((int) $analysis->frameworkid))->build();

        // The analysis describes what was actually sent, which may differ from when it was requested.
        $analysis->resourcehash = $extracted['hash'];
        $analysis->cataloguehash = $catalogue->hash;
        if (!empty($extracted['provenance'])) {
            $analysis->provenance = json_encode($extracted['provenance'], JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
        }

        [$resource, $provenance] = $this->service_resource($extracted, (string) $analysis->requestid);
        if ($provenance !== null) {
            $analysis->provenance = $provenance;
        }
        $request = [
            'schema_version' => alignment_client::SCHEMA_VERSION,
            'resource' => $resource,
            'competencies' => $catalogue->items,
            'config' => [
                'top_k' => (int) $analysis->topk,
                'max_suggestions' => (int) $analysis->maxsuggestions,
            ],
        ];

        $response = ($this->clientfactory)()->analyse($request, (string) $analysis->requestid);

        $validated = response_validator::validate(
            $response,
            $resource['resource_id'],
            $catalogue->idnumbers(),
            (int) $analysis->topk,
            (int) $analysis->maxsuggestions,
            $resource['text']
        );

        $this->store($analysis, $validated, $catalogue);
    }

    /**
     * Store a validated answer: the analysis outcome, the suggestions and their evidence.
     *
     * Everything is written in one transaction, so an error leaves no partial result behind.
     *
     * @param \stdClass $analysis The running analysis.
     * @param array $validated The answer as returned by response_validator::validate().
     * @param catalogue_snapshot $catalogue The catalogue that was sent.
     */
    private function store(\stdClass $analysis, array $validated, catalogue_snapshot $catalogue): void {
        global $DB;

        $now = time();
        $transaction = $DB->start_delegated_transaction();

        try {
            $analysis->status = self::STATUS_COMPLETED;
            $analysis->backend = $validated['backend'];
            $analysis->model = $validated['model'];
            $analysis->externalanalysisid = $validated['analysisid'];
            $analysis->completeness = $validated['completeness'];
            $analysis->abstained = $validated['abstained'] ? 1 : 0;
            $analysis->diagnostics = json_encode($validated['diagnostics'], JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
            $analysis->manifest = json_encode($validated['manifest'], JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
            $analysis->errorcode = null;
            $analysis->errormessage = null;
            $analysis->timecompleted = $now;
            $DB->update_record('local_compalign_analysis', $analysis);

            foreach ($validated['suggestions'] as $order => $suggestion) {
                $competency = $catalogue->find($suggestion['idnumber']);
                $suggestionid = $DB->insert_record('local_compalign_sugg', (object) [
                    'analysisid' => $analysis->id,
                    'competencyid' => $competency['id'],
                    'competencyidnumber' => $suggestion['idnumber'],
                    'confidence' => $suggestion['confidence'],
                    'bm25rank' => $suggestion['bm25rank'],
                    'supportcount' => $suggestion['supportcount'],
                    'sortorder' => $order,
                    'warnings' => json_encode($suggestion['warnings'], JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR),
                    'timecreated' => $now,
                ]);

                foreach ($suggestion['evidence'] as $position => $item) {
                    $DB->insert_record('local_compalign_evidence', (object) [
                        'suggestionid' => $suggestionid,
                        'fragmentid' => $item['fragmentid'],
                        'evidencetext' => $item['quote'],
                        'evidenceorder' => $position,
                    ]);
                }
            }

            $transaction->allow_commit();
        } catch (\Throwable $exception) {
            // Roll back first, so the failure update that follows is not swallowed with the transaction.
            $transaction->rollback($exception);
        }
    }

    /**
     * The resource fields the service accepts, after a file has been turned into text.
     *
     * @param array $extracted The adapter result.
     * @param string $requestid Correlation id for the extraction call.
     * @return array{0: array<string, string>, 1: string|null} Resource body, and provenance JSON when a file was read.
     */
    private function service_resource(array $extracted, string $requestid): array {
        $resource = $extracted['resource'];
        $provenance = null;

        if (!empty($extracted['file'])) {
            $filetext = $this->file_text($extracted['file'], $requestid);
            $resource['text'] = $filetext['text'];
            $resource['search_text'] = resource_extractor::combine_text($resource['title'] ?? '', $filetext['text']);
            $details = $extracted['provenance'] ?? [];
            $details['segments'] = $filetext['segments'];
            $provenance = json_encode($details, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
        }

        $allowed = [
            'resource_id', 'resource_type', 'course_id', 'course_module_id', 'title', 'text',
            'search_text', 'course_shortname', 'course_fullname', 'section_name', 'activity_name',
        ];

        return [array_intersect_key($resource, array_flip($allowed)), $provenance];
    }

    /**
     * Plain text for a teacher file, from the extraction cache or the service.
     *
     * @param array<string, string> $file File identity from the adapter.
     * @param string $requestid Correlation id.
     * @return array{text: string, segments: array}
     */
    private function file_text(array $file, string $requestid): array {
        global $DB;

        $cached = $DB->get_record('local_compalign_extract', [
            'contenthash' => $file['contenthash'],
            'extractorversion' => \local_compalign\resource\file_item::EXTRACTOR_VERSION,
        ]);
        if ($cached) {
            $segments = json_decode((string) $cached->provenance, true);
            return [
                'text' => (string) $cached->canonicaltext,
                'segments' => is_array($segments) ? $segments : [],
            ];
        }

        $stored = get_file_storage()->get_file_by_id((int) $file['fileid']);
        if (!$stored) {
            throw new analysis_exception('resource_missing');
        }

        $result = ($this->clientfactory)()->extract_document(
            $stored->get_content(),
            $file['format'],
            $file['filename'],
            $requestid
        );
        $DB->insert_record('local_compalign_extract', (object) [
            'contenthash' => $file['contenthash'],
            'extractorversion' => \local_compalign\resource\file_item::EXTRACTOR_VERSION,
            'canonicaltext' => $result['text'],
            'provenance' => json_encode($result['segments'], JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR),
            'timecreated' => time(),
        ]);

        return $result;
    }

    /**
     * Mark an analysis as failed.
     *
     * @param \stdClass $analysis The analysis.
     * @param string $code Stable error code.
     * @param string $message Safe message for administrators.
     * @param string[] $details Specific problems, safe for administrators.
     */
    private function fail(\stdClass $analysis, string $code, string $message, array $details = []): void {
        global $DB;

        $text = trim($message . ($details ? ' ' . implode('; ', $details) : ''));

        $DB->update_record('local_compalign_analysis', (object) [
            'id' => $analysis->id,
            'status' => self::STATUS_FAILED,
            'errorcode' => mb_substr($code, 0, 60),
            'errormessage' => mb_substr($text, 0, self::MAX_ERROR_MESSAGE_CHARS),
            'timecompleted' => time(),
        ]);
    }
}
