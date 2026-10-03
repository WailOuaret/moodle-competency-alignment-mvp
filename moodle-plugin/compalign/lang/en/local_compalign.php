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
$string['coursenotyet'] = 'Suggestions for the resources of this course are added in the next release of the assistant.';

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
$string['privacy:metadata:local_compalign_analysis:requestedby'] = 'The user who requested the analysis.';
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
