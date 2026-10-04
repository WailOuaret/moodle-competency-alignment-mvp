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
 * English language strings for the Competency Alignment Assistant.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

$string['pluginname'] = 'Competency Alignment Assistant';
$string['competencyalignment'] = 'Competency Alignment';

// Capabilities.
$string['compalign:view'] = 'View the Competency Alignment Assistant';
$string['compalign:analyse'] = 'Request competency suggestions for a resource';
$string['compalign:review'] = 'Accept, reject or modify suggested competencies';
$string['compalign:writeback'] = 'Write approved competencies to Moodle';
$string['compalign:viewallreviews'] = 'View the reviews of all teachers';
$string['compalign:manage'] = 'Manage the Competency Alignment Assistant';

// Settings.
$string['servicesettings'] = 'Alignment service';
$string['servicesettings_desc'] = 'The assistant sends the text of a teacher-authored resource and the competency catalogue to a separate Python alignment service. The service holds the model credentials. Moodle holds only the address and token below.';
$string['serviceurl'] = 'Alignment service URL';
$string['serviceurl_desc'] = 'Base URL of the alignment service, for example https://alignment.example.org. Plain http:// is accepted only for local development hosts: localhost, host.docker.internal and private IP addresses.';
$string['serviceurl_invalid'] = 'Enter a base URL such as https://alignment.example.org, without credentials, query or fragment.';
$string['serviceurl_httpsrequired'] = 'Use https:// for this host. Plain http:// is accepted only for localhost, host.docker.internal and private IP addresses.';
$string['servicetoken'] = 'Alignment service token';
$string['servicetoken_desc'] = 'Shared secret sent to the service as a bearer token. It is stored encrypted and is never shown again. Leave the field untouched to keep the current token.';
$string['requesttimeout'] = 'Request timeout';
$string['requesttimeout_desc'] = 'Seconds to wait for the alignment service before an analysis is marked as failed ({$a->min} to {$a->max}).';
$string['requesttimeout_invalid'] = 'Enter a whole number of seconds from {$a->min} to {$a->max}.';
$string['topk'] = 'Top-K';
$string['topk_fixed'] = 'Fixed at {$a}. The first plugin prototype uses Top-K={$a}, matching the evaluated research configuration. The alignment service refuses any other value.';
$string['maxsuggestions'] = 'Maximum suggestions';
$string['maxsuggestions_desc'] = 'The largest number of competencies proposed for one resource.';
$string['enablewriteback'] = 'Enable official write-back';
$string['enablewriteback_desc'] = 'Reserved. Writing accepted competencies to Moodle activity links is not implemented in this release, so this setting has no effect yet. It is off by default and stays off until the feature has been tested.';
$string['requirehumanreview'] = 'Require human review';
$string['requirehumanreview_desc'] = 'Always on. Nothing is written to Moodle until a teacher has accepted or modified a suggestion. This cannot be changed.';
$string['connectionstatus'] = 'Connection status';
$string['connectionstatus_link'] = 'Open the plugin overview to check the connection to the alignment service.';

// Overview and connection status.
$string['overview_release'] = 'Release';
$string['overview_writeback'] = 'Official write-back';
$string['overview_humanreview'] = 'Human review';
$string['overview_topk'] = 'Top-K';
$string['writeback_off'] = 'Off. Suggestions are only stored with the teacher\'s decision. No Moodle competency link is created.';
$string['humanreview_always'] = 'Always required';
$string['connectionchecked'] = 'Checked {$a}';
$string['status_connected'] = 'Connected';
$string['status_connected_help'] = 'The service answered and accepted the configured token.';
$string['status_unavailable'] = 'Service unavailable';
$string['status_unavailable_help'] = 'The service did not answer, or answered with a server error. Check that it is running and that the URL is correct.';
$string['status_unauthorized'] = 'Unauthorized';
$string['status_unauthorized_help'] = 'The service is reachable but rejected the token. Enter the token that is configured on the service.';
$string['status_invalidresponse'] = 'Invalid response';
$string['status_invalidresponse_help'] = 'Something answered, but it does not look like the alignment service. Check the URL.';
$string['status_blocked'] = 'Blocked by Moodle';
$string['status_blocked_help'] = 'Moodle\'s HTTP security settings refuse this address or port. An administrator can allow it under Site administration > General > Security > HTTP security.';
$string['status_notconfigured'] = 'Not configured';
$string['status_notconfigured_help'] = 'Enter the service URL and token in the plugin settings.';
$string['status_notconfigured_url'] = 'The service URL is missing or not valid. Check it in the plugin settings.';
$string['status_notconfigured_token'] = 'The service token is missing or cannot be read. Enter it again in the plugin settings.';
$string['opensettings'] = 'Open the plugin settings';

// Competency framework setting.
$string['frameworkid'] = 'Competency framework';
$string['frameworkid_desc'] = 'The framework the assistant proposes competencies from. Only this one framework is used; frameworks are never combined. Every competency in it needs an ID number and a description.';
$string['framework_none'] = 'Not selected';
$string['framework_nocompetencies'] = 'Competencies are disabled on this site, so no framework can be chosen.';

// Dashboard.
$string['dashboard_intro'] = 'Ask the assistant to suggest competencies for a resource, then review each suggestion. The assistant only proposes: nothing is written to Moodle competency links.';
$string['dashboard_noresources'] = 'This course has no resources yet.';
$string['dashboard_notready'] = 'The assistant is not ready to analyse resources';
$string['column_resource'] = 'Resource';
$string['column_type'] = 'Type';
$string['column_status'] = 'Analysis';
$string['column_links'] = 'Current Moodle competency links';
$string['column_action'] = 'Action';
$string['linksnone'] = 'None';
$string['viewsuggestions'] = 'View suggestions';
$string['analysis_none'] = 'Not analysed';
$string['analysis_queued'] = 'Queued';
$string['analysis_running'] = 'Analysing';
$string['analysis_ready'] = 'Suggestions ready';
$string['analysis_nosuggestion'] = 'Analysed, no suggestion';
$string['analysis_reviewed'] = 'Reviewed';
$string['analysis_failed'] = 'Failed';
$string['analysis_progress'] = '{$a->reviewed} of {$a->total} reviewed';
$string['plugin_overview'] = 'Plugin overview';

// Resource page.
$string['reviewheading'] = 'Competency suggestions: {$a}';
$string['backtodashboard'] = 'Back to Competency Alignment';
$string['officiallinks'] = 'Current Moodle competency links';
$string['officiallinks_none'] = 'No competency is linked to this resource yet.';
$string['noanalysis'] = 'No analysis has been requested for this resource yet.';
$string['analysis_queued_hint'] = 'The analysis starts when Moodle next runs its background tasks (cron). This page refreshes by itself.';
$string['analysis_running_hint'] = 'The resource is being analysed. This page refreshes by itself.';
$string['analysis_changed_page'] = 'This page was edited after the analysis, so the evidence below may no longer match it. Use Reanalyse before you decide.';
$string['analysis_changed_framework'] = 'The competency framework was changed after the analysis, so these suggestions may be out of date. Use Reanalyse before you decide.';
$string['analysis_failed_heading'] = 'The analysis did not complete';
$string['analysis_failed_hint'] = 'Nothing was changed in your course. When the problem is fixed, use Reanalyse to try again.';
$string['analysisqueued'] = 'The analysis was queued.';
$string['analysisactive'] = 'An analysis is already in progress for this resource.';
$string['analysisreused'] = 'An identical analysis already exists, so no new request was made. Use Reanalyse to run it again.';
$string['reanalyse'] = 'Reanalyse';
$string['reanalyse_help'] = 'Sends the resource to the alignment service again and replaces the suggestions you see here. Your earlier decisions are kept.';
$string['analysisabstained'] = 'The assistant found no competency with direct evidence in this resource, so it suggested none.';
$string['analysispartial'] = 'Some parts of this resource could not be analysed, so the suggestions below may be incomplete.';
$string['backend_mock_notice'] = 'This analysis used the test backend. Its suggestions are placeholders and are not model output.';
$string['writebackoffnotice'] = 'Official write-back is off. Saving a decision does not create or change any Moodle competency link.';
$string['nopermissiontoreview'] = 'You can see these suggestions but you may not review them.';
$string['nopermissiontoanalyse'] = 'You may not ask for suggestions for this resource.';

// Suggestion card.
$string['proposedcompetency'] = 'Suggested competency';
$string['competencycode'] = 'Code';
$string['competencyname'] = 'Name';
$string['competencydescription'] = 'Description';
$string['evidenceheading'] = 'Exact evidence from the resource';
$string['technicaldetails'] = 'Technical details';
$string['bm25rank'] = 'Search rank (BM25)';
$string['modelconfidence'] = 'Model confidence (not a probability)';
$string['supportcount'] = 'Supporting passages';
$string['passages'] = 'Passages';
$string['englishlabel'] = 'English label';
$string['catalogueid'] = 'Catalogue identifier';
$string['sourceuri'] = 'Source';
$string['unknownvalue'] = 'Not available';
$string['hierarchywarning'] = 'Hierarchy note';
$string['warning_parent_child_redundancy_parent'] = 'A more specific child competency ({$a}) is also suggested for this resource.';
$string['warning_parent_child_redundancy_child'] = 'Its parent competency ({$a}) is also suggested for this resource.';
$string['warning_granularity_conflict_parent'] = 'A more specific child competency ({$a}) is suggested with overlapping evidence.';
$string['warning_granularity_conflict_child'] = 'Its parent competency ({$a}) is suggested with overlapping evidence.';
$string['warning_generic'] = 'A hierarchy check flagged this competency.';

// Review form.
$string['decision'] = 'Decision';
$string['finalcompetency'] = 'Replacement competency';
$string['finalcompetency_help'] = 'Choose the competency that fits this resource better. It is used only when you choose Modify.';
$string['choosecompetency'] = 'Choose a competency...';
$string['usefulness_0'] = 'Did not help justify the decision';
$string['usefulness_1'] = 'Partly useful';
$string['usefulness_2'] = 'Clearly supported the decision';
$string['evidenceusefulness_help'] = 'Optional. How useful was the evidence in reaching your decision?';
$string['comment_help'] = 'Optional. Mention anything that was difficult, ambiguous or unclear.';
$string['decisionsaved'] = 'Your decision was saved. Nothing was written to Moodle competency links.';
$string['yourdecision'] = 'Your decision';
$string['notreviewed'] = 'Not reviewed yet';
$string['decision_accept_summary'] = 'Accepted';
$string['decision_reject_summary'] = 'Rejected';
$string['decision_modify_summary'] = 'Modified to {$a}';
$string['revisionsaved'] = 'Revision {$a->revision}, saved {$a->time}';
$string['changedecision'] = 'Change your decision';

// Form validation.
$string['error_decisionrequired'] = 'Choose accept, reject or modify.';
$string['error_modifyneedscompetency'] = 'Choose the competency that replaces the suggestion.';
$string['error_invalidcompetency'] = 'That competency is not in the configured framework.';
$string['error_modifysame'] = 'Choose a competency other than the suggested one, or accept the suggestion.';
$string['error_invalidusefulness'] = 'Choose one of the three ratings, or leave it empty.';
$string['error_commenttoolong'] = 'The comment is longer than {$a} characters.';

// Why an analysis could not run or complete. The stored code is mapped to one of these sentences.
$string['error_generic'] = 'The analysis could not be completed.';
$string['error_notconfigured_url'] = 'The alignment service address is not set. Ask an administrator to set it in the plugin settings.';
$string['error_notconfigured_token'] = 'The alignment service token is not set. Ask an administrator to set it in the plugin settings.';
$string['error_framework_not_selected'] = 'No competency framework has been selected for the assistant. Ask an administrator to choose one in the plugin settings.';
$string['error_competencies_disabled'] = 'Competencies are disabled on this site, so the assistant cannot suggest any.';
$string['error_framework_unavailable'] = 'The selected competency framework cannot be read. Ask an administrator to check the plugin settings.';
$string['error_framework_hidden'] = 'The selected competency framework is hidden. Ask an administrator to choose a visible one.';
$string['error_framework_empty'] = 'The selected competency framework has no competencies.';
$string['error_framework_invalid'] = 'The selected competency framework cannot be used yet. Every competency needs an ID number and a description.';
$string['error_unsupported_resource_type'] = 'Unsupported resource type.';
$string['error_unsupported_question_type'] = 'Question type not supported for alignment.';
$string['error_resource_item_required'] = 'Choose one question, chapter or file. This activity contains more than one.';
$string['error_document_no_text'] = 'This PDF does not contain enough extractable text. OCR is not enabled in this release.';
$string['error_document_malformed'] = 'The document could not be read.';
$string['error_document_encrypted'] = 'This document is password-protected and cannot be analysed.';
$string['error_document_too_large'] = 'The document is too large for analysis.';
$string['error_document_unsupported'] = 'Unsupported resource type.';
$string['unsupportedtype'] = 'Unsupported resource type.';
$string['unsupportedquestion'] = 'Question type not supported for alignment.';
$string['unsupportedfile'] = 'Unsupported resource type.';
$string['filetoolarge'] = 'The document is too large for analysis.';
$string['resourceempty'] = 'This resource has no text to analyse.';
$string['analysis_stale'] = 'Stale';
$string['analysis_unsupported'] = 'Unsupported';
$string['batch_legend'] = 'Analyse selected items';
$string['batch_help'] = 'Tick at most {$a} items. Each one is a separate analysis. Nothing starts until you submit.';
$string['batch_submit'] = 'Analyse selected';
$string['batch_toomany'] = 'Select at most {$a} items.';
$string['batch_none'] = 'Select at least one item.';
$string['batch_queued'] = '{$a} analyses were queued.';
$string['batch_confirm'] = 'Confirm analysis';
$string['batch_preview'] = '{$a->cached} items already have a current analysis. {$a->fresh} items would call the model. {$a->active} items are already running.';
$string['filter_all'] = 'All';
$string['filter_supported'] = 'Supported';
$string['filter_none'] = 'Not analysed';
$string['filter_ready'] = 'Suggestions ready';
$string['filter_reviewed'] = 'Reviewed';
$string['filter_stale'] = 'Stale';
$string['filter_failed'] = 'Failed';
$string['type_all'] = 'All types';
$string['type_page'] = 'Pages';
$string['type_quiz'] = 'Quiz questions';
$string['type_document'] = 'Documents';
$string['type_transcript'] = 'Video transcripts';
$string['type_other'] = 'Other';
$string['evidence_page'] = 'Page {$a}';
$string['evidence_slide'] = 'Slide {$a}';
$string['evidence_section'] = 'Section {$a}';
$string['evidence_time'] = '{$a->start}–{$a->end}';
$string['transcript_required'] = 'Transcript required for video alignment.';
$string['error_resource_not_accessible'] = 'You cannot see this resource, so it cannot be analysed.';
$string['error_resource_missing'] = 'This resource no longer exists.';
$string['error_resource_empty'] = 'This page has no text to analyse.';
$string['error_resource_too_large'] = 'This page is too long to analyse.';
$string['error_busy'] = 'Another request for this resource is being handled. Try again in a moment.';
$string['error_unavailable'] = 'The alignment service could not be reached.';
$string['error_unauthorized'] = 'The alignment service did not accept the plugin\'s credentials. Ask an administrator to check the token.';
$string['error_blocked'] = 'Moodle\'s HTTP security settings blocked the request to the alignment service. Ask an administrator.';
$string['error_invalid_response'] = 'The alignment service answered with something that did not pass validation. No suggestion was stored.';
$string['error_model_output_invalid'] = 'The model did not return a suggestion that passed validation. No suggestion was stored.';
$string['error_backend_unavailable'] = 'The model behind the alignment service is not available right now.';
$string['error_service'] = 'The alignment service refused the request ({$a}).';
$string['error_internal_error'] = 'The analysis failed unexpectedly. An administrator can find details in the Moodle logs.';
$string['error_invalid_review'] = 'The decision could not be saved.';

// Framework problems found while reading the framework.
$string['catalogueproblem_noidnumber'] = '{$a}: the competency has no ID number.';
$string['catalogueproblem_duplicate'] = '{$a}: the ID number is used twice.';
$string['catalogueproblem_nodescription'] = '{$a}: the competency has no description.';
$string['catalogueproblem_parent'] = '{$a}: its parent competency has no ID number.';

// Events and tasks.
$string['event_analysis_requested'] = 'Competency suggestions requested';
$string['event_review_saved'] = 'Competency suggestion reviewed';
$string['task_analyse_resource'] = 'Analyse a resource for competency suggestions';

// Review vocabulary.
$string['analyse'] = 'Analyse';
$string['suggestcompetencies'] = 'Suggest competencies';
$string['accept'] = 'Accept';
$string['reject'] = 'Reject';
$string['modify'] = 'Modify';
$string['evidenceusefulness'] = 'Evidence usefulness';
$string['comment'] = 'Comment';
$string['savedecision'] = 'Save decision';

// Privacy.
$string['privacy:metadata:local_compalign_analysis'] = 'Requests to analyse a learning resource against a competency framework.';
$string['privacy:metadata:local_compalign_analysis:courseid'] = 'The course of the analysed resource.';
$string['privacy:metadata:local_compalign_analysis:cmid'] = 'The course module of the analysed resource.';
$string['privacy:metadata:local_compalign_analysis:sourceitemid'] = 'The stable id of the Page, question, chapter, file or other item that was analysed.';
$string['privacy:metadata:local_compalign_analysis:provenance'] = 'Where the analysed text came from, such as a question slot, a page number or a caption time.';
$string['privacy:metadata:local_compalign_analysis:requestedby'] = 'The user who requested the analysis.';
$string['privacy:metadata:local_compalign_extract'] = 'Cached text extracted from a teacher file. The cache has no user id. The file itself could contain a name if a teacher put one in the document.';
$string['privacy:metadata:local_compalign_extract:contenthash'] = 'The Moodle content hash of the file.';
$string['privacy:metadata:local_compalign_extract:canonicaltext'] = 'The text extracted from the file.';
$string['privacy:metadata:local_compalign_extract:timecreated'] = 'The time the text was extracted.';
$string['privacy:metadata:local_compalign_analysis:timecreated'] = 'The time the analysis was requested.';
$string['privacy:metadata:local_compalign_review'] = 'Teacher decisions on competencies suggested for a resource.';
$string['privacy:metadata:local_compalign_review:userid'] = 'The teacher who made the decision.';
$string['privacy:metadata:local_compalign_review:decision'] = 'Whether the teacher accepted, rejected or modified the suggestion.';
$string['privacy:metadata:local_compalign_review:finalcompetencyidnumber'] = 'The competency the teacher approved, if any.';
$string['privacy:metadata:local_compalign_review:evidenceusefulness'] = 'The teacher\'s rating of how useful the evidence was.';
$string['privacy:metadata:local_compalign_review:commenttext'] = 'The optional comment the teacher wrote.';
$string['privacy:metadata:local_compalign_review:reviewdurationseconds'] = 'How long the teacher took to review the suggestion.';
$string['privacy:metadata:local_compalign_review:timecreated'] = 'The time the decision was saved.';
$string['privacy:metadata:alignmentservice'] = 'The configured alignment service receives the text of the analysed resource and the competency catalogue. It receives no information about users.';
$string['privacy:metadata:alignmentservice:resourcetitle'] = 'The title of the analysed resource.';
$string['privacy:metadata:alignmentservice:resourcetext'] = 'The teacher-authored text of the analysed resource.';
$string['privacy:metadata:alignmentservice:competencies'] = 'The names and descriptions of the competencies in the configured framework.';
$string['privacy:path:analyses'] = 'Analyses requested';
$string['privacy:path:reviews'] = 'Competency reviews';
