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

/**
 * Competency suggestions for one resource, and the teacher's decisions on them.
 *
 * This page can start an analysis and save a decision. Both are state changes, so both need a POST,
 * a valid session key and the matching capability. The reviewer is always the logged-in user.
 * Nothing here writes a Moodle competency link.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

require_once(__DIR__ . '/../../config.php');

use core\output\notification;
use local_compalign\form\review_form;
use local_compalign\output\error_messages;
use local_compalign\output\review_page;
use local_compalign\service\analysis_exception;
use local_compalign\service\analysis_manager;
use local_compalign\service\competency_catalogue;
use local_compalign\service\competency_links;
use local_compalign\service\resource_extractor;
use local_compalign\service\review_manager;

$cmid = required_param('cmid', PARAM_INT);
$action = optional_param('action', '', PARAM_ALPHA);

[$course, $cm] = get_course_and_cm_from_cmid($cmid);
require_login($course, false, $cm);
$context = context_module::instance($cm->id);
require_capability('local/compalign:view', $context);

$url = new moodle_url('/local/compalign/review.php', ['cmid' => $cm->id]);
$PAGE->set_url($url);
$PAGE->set_context($context);
$PAGE->set_title(get_string('pluginname', 'local_compalign'));
$PAGE->set_heading($course->fullname);
$PAGE->set_pagelayout('incourse');
$PAGE->navbar->add(
    get_string('competencyalignment', 'local_compalign'),
    new moodle_url('/local/compalign/index.php', ['courseid' => $course->id])
);
$PAGE->navbar->add($cm->get_formatted_name());

$manager = new analysis_manager();
$supported = resource_extractor::supports($cm);
$canreview = has_capability('local/compalign:review', $context);
$cananalyse = has_capability('local/compalign:analyse', $context);

// Start or repeat an analysis. Only a POST with a valid session key and the capability gets this far.
if ($supported && in_array($action, ['analyse', 'reanalyse'], true) && data_submitted()) {
    require_sesskey();
    require_capability('local/compalign:analyse', $context);

    try {
        $result = $manager->request_analysis($cm, (int) $USER->id, $action === 'reanalyse');
        $messages = [
            analysis_manager::OUTCOME_QUEUED => ['analysisqueued', notification::NOTIFY_SUCCESS],
            analysis_manager::OUTCOME_ACTIVE => ['analysisactive', notification::NOTIFY_INFO],
            analysis_manager::OUTCOME_REUSED => ['analysisreused', notification::NOTIFY_INFO],
        ];
        [$string, $type] = $messages[$result['outcome']];
        redirect($url, get_string($string, 'local_compalign'), null, $type);
    } catch (analysis_exception $exception) {
        redirect($url, error_messages::for_code($exception->get_error_code()), null, notification::NOTIFY_ERROR);
    }
}

$analysis = $supported ? $manager->get_latest((int) $cm->id) : null;
$notices = [];
$catalogue = null;
$suggestions = [];
$reviews = [];
$forms = [];
$formhtml = [];

if (!$supported) {
    $notices[] = ['type' => 'info', 'text' => get_string('unsupportedtype', 'local_compalign')];
}

if ($analysis !== null) {
    // The names and the choices for a modification come from the framework the analysis used, as it is now.
    try {
        $catalogue = (new competency_catalogue((int) $analysis->frameworkid))->build();
    } catch (analysis_exception $exception) {
        $notices[] = ['type' => 'warning', 'text' => error_messages::for_code($exception->get_error_code())];
    }
}

if ($analysis !== null && $analysis->status === analysis_manager::STATUS_COMPLETED) {
    // The evidence was exact when it was stored. Say so when the Page or the framework has moved on.
    foreach ($manager->find_changes($analysis, $cm, $catalogue) as $change) {
        $notices[] = ['type' => 'warning', 'text' => get_string('analysis_changed_' . $change, 'local_compalign')];
    }

    $suggestions = $manager->get_suggestions((int) $analysis->id);
    $reviewmanager = new review_manager();
    $reviews = $reviewmanager->latest_reviews((int) $analysis->id, (int) $USER->id);

    if ($suggestions && $canreview && $catalogue !== null) {
        foreach ($suggestions as $suggestion) {
            $proposed = (string) $suggestion->competencyidnumber;
            $choices = [];
            foreach ($catalogue->lookup as $idnumber => $competency) {
                if ((string) $idnumber !== $proposed) {
                    $choices[(string) $idnumber] = $idnumber . ' - ' . $competency['shortname'];
                }
            }
            ksort($choices);

            $form = new review_form($url, [
                'cmid' => $cm->id,
                'suggestionid' => (int) $suggestion->id,
                'proposedidnumber' => $proposed,
                'choices' => $choices,
                'validids' => $catalogue->idnumbers(),
            ]);

            $previous = $reviews[(int) $suggestion->id] ?? null;
            if ($previous !== null) {
                $form->set_data([
                    'decision' => $previous->decision,
                    'finalcompetency' => $previous->decision === review_manager::DECISION_MODIFY
                        ? $previous->finalcompetencyidnumber
                        : '',
                    'usefulness' => $previous->evidenceusefulness,
                    'commenttext' => $previous->commenttext,
                ]);
            }

            $forms[(int) $suggestion->id] = $form;
        }

        // Save a decision. The time the card was first shown is read from the server-side session.
        foreach ($forms as $suggestionid => $form) {
            if (!($data = $form->get_data())) {
                continue;
            }

            $key = $analysis->id . ':' . $suggestionid;
            try {
                $reviewmanager->save(
                    $analysis,
                    $suggestions[$suggestionid],
                    (int) $USER->id,
                    (string) $data->decision,
                    isset($data->finalcompetency) ? (string) $data->finalcompetency : null,
                    $data->usefulness ?? null,
                    isset($data->commenttext) ? (string) $data->commenttext : null,
                    $SESSION->local_compalign_started[$key] ?? null,
                    $catalogue
                );
            } catch (analysis_exception $exception) {
                $notices[] = [
                    'type' => 'danger',
                    'text' => error_messages::for_code($exception->get_error_code()),
                ];
                break;
            }

            unset($SESSION->local_compalign_started[$key]);
            redirect(
                new moodle_url($url, [], 'suggestion-' . $suggestionid),
                get_string('decisionsaved', 'local_compalign'),
                null,
                notification::NOTIFY_SUCCESS
            );
        }

        // The review time starts when a card is first shown to this teacher.
        $SESSION->local_compalign_started = $SESSION->local_compalign_started ?? [];
        foreach ($forms as $suggestionid => $form) {
            $SESSION->local_compalign_started[$analysis->id . ':' . $suggestionid] ??= time();
            $formhtml[$suggestionid] = $form->render();
        }
    } else if ($suggestions && !$canreview) {
        $notices[] = ['type' => 'info', 'text' => get_string('nopermissiontoreview', 'local_compalign')];
    }
}

// The button that starts or repeats the analysis.
$actionhtml = '';
$finished = $analysis !== null
    && in_array($analysis->status, [analysis_manager::STATUS_COMPLETED, analysis_manager::STATUS_FAILED], true);
if ($supported && $cananalyse && ($analysis === null || $finished)) {
    $label = $analysis === null ? 'suggestcompetencies' : 'reanalyse';
    $actionhtml = $OUTPUT->render(new single_button(
        new moodle_url($url, ['action' => $analysis === null ? 'analyse' : 'reanalyse']),
        get_string($label, 'local_compalign'),
        'post',
        $analysis === null ? single_button::BUTTON_PRIMARY : single_button::BUTTON_SECONDARY
    ));
    if ($analysis !== null) {
        $actionhtml .= html_writer::div(get_string('reanalyse_help', 'local_compalign'), 'form-text');
    }
}

// While the analysis waits or runs, the page asks the browser to look again. No script is needed.
if ($analysis !== null
        && in_array($analysis->status, [analysis_manager::STATUS_QUEUED, analysis_manager::STATUS_RUNNING], true)) {
    header('Refresh: 5; url=' . $url->out(false));
}

echo $OUTPUT->header();
echo $OUTPUT->heading(get_string('pluginname', 'local_compalign'));
echo $OUTPUT->render(new review_page(
    $cm,
    $supported,
    $analysis,
    $suggestions,
    $catalogue,
    $reviews,
    $formhtml,
    competency_links::list_for_cm($cm),
    $notices,
    $actionhtml
));
echo $OUTPUT->footer();
