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

namespace local_compalign\form;

use local_compalign\service\review_manager;

// The autoloader includes this file from inside a function, so the global has to be declared.
global $CFG;
require_once($CFG->libdir . '/formslib.php');

/**
 * The decision form shown under one suggested competency.
 *
 * A review page holds one of these forms per suggestion, so each form takes its identifier from the
 * suggestion it belongs to. Nothing is preselected. The rules are the ones in review_manager: the
 * form only shows the errors that class finds, and the saver checks them again.
 *
 * The form never carries the reviewer: the page uses the logged-in user.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class review_form extends \moodleform {
    /**
     * Give each suggestion its own form identifier, so several forms can share one page.
     *
     * @return string
     */
    protected function get_form_identifier() {
        return 'local_compalign_review_' . (int) ($this->_customdata['suggestionid'] ?? 0);
    }

    /**
     * Define the form.
     */
    protected function definition() {
        $mform = $this->_form;
        $custom = $this->_customdata;

        // The page address carries the course module id, and Moodle renders an address's parameters as hidden
        // fields, so it is not declared here a second time.
        $mform->addElement('hidden', 'suggestionid', (int) $custom['suggestionid']);
        $mform->setType('suggestionid', PARAM_INT);

        $decisions = [];
        foreach (review_manager::DECISIONS as $decision) {
            $decisions[] = $mform->createElement('radio', 'decision', '', get_string($decision, 'local_compalign'), $decision);
        }
        $mform->addGroup($decisions, 'decisiongroup', get_string('decision', 'local_compalign'), ['<br>'], false);

        // Only the other competencies of the framework can replace the suggestion.
        $choices = ['' => get_string('choosecompetency', 'local_compalign')] + $custom['choices'];
        $mform->addElement('select', 'finalcompetency', get_string('finalcompetency', 'local_compalign'), $choices);
        $mform->addHelpButton('finalcompetency', 'finalcompetency', 'local_compalign');
        // Moodle hides this once Accept or Reject is chosen. It does not hide it while no radio is
        // checked, so styles.css keeps the row hidden until Modify is selected. Saving still checks
        // the decision on the server, whether or not the row was visible.
        $mform->hideIf('finalcompetency', 'decision', 'neq', review_manager::DECISION_MODIFY);

        // The rating is optional and nothing is preselected. The values are strings on purpose: with the
        // integer 0 an unset form compares equal to it (null == 0) and would tick "did not help" by default.
        $ratings = [];
        foreach (review_manager::USEFULNESS_VALUES as $value) {
            $label = $value . ' - ' . get_string('usefulness_' . $value, 'local_compalign');
            $ratings[] = $mform->createElement('radio', 'usefulness', '', $label, (string) $value);
        }
        $mform->addGroup($ratings, 'usefulnessgroup', get_string('evidenceusefulness', 'local_compalign'), ['<br>'], false);
        $mform->addHelpButton('usefulnessgroup', 'evidenceusefulness', 'local_compalign');

        $mform->addElement('textarea', 'commenttext', get_string('comment', 'local_compalign'), [
            'rows' => 3,
            'cols' => 60,
            'maxlength' => review_manager::MAX_COMMENT_CHARS,
        ]);
        $mform->setType('commenttext', PARAM_TEXT);
        $mform->addHelpButton('commenttext', 'comment', 'local_compalign');

        $this->add_action_buttons(false, get_string('savedecision', 'local_compalign'));
    }

    /**
     * Server-side validation, using the same rules as the saver.
     *
     * @param array $data The submitted values.
     * @param array $files The submitted files.
     * @return array Errors keyed by element name.
     */
    public function validation($data, $files) {
        $errors = parent::validation($data, $files);

        // A radio group drops a value that is not one of its options before validation runs, so a rating
        // that was tampered with would look like "not rated". The value is read as it was submitted.
        $submittedrating = $this->_form->getSubmitValue('usefulness');

        $found = review_manager::find_errors(
            (string) ($data['decision'] ?? ''),
            isset($data['finalcompetency']) ? (string) $data['finalcompetency'] : null,
            $submittedrating,
            isset($data['commenttext']) ? (string) $data['commenttext'] : null,
            (string) $this->_customdata['proposedidnumber'],
            $this->_customdata['validids']
        );

        $elements = ['decision' => 'decisiongroup', 'usefulness' => 'usefulnessgroup'];
        foreach ($found as $field => $message) {
            $errors[$elements[$field] ?? $field] = $message;
        }

        return $errors;
    }
}
