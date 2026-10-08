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

use local_compalign\output\error_messages;
use local_compalign\service\catalogue_snapshot;
use local_compalign\service\manual_relationship;

defined('MOODLE_INTERNAL') || die();

global $CFG;
require_once($CFG->libdir . '/formslib.php');

/**
 * Form for adding a competency the model did not suggest.
 *
 * The list contains only the configured framework. The server checks the same
 * rules again when the form is saved.
 *
 * @package    local_compalign
 * @copyright  2026 Wail Ouaret
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class add_competency_form extends \moodleform {
    /**
     * Define the fields.
     */
    public function definition() {
        $mform = $this->_form;
        /** @var catalogue_snapshot $catalogue */
        $catalogue = $this->_customdata['catalogue'];
        $choices = [];
        foreach ($catalogue->lookup as $idnumber => $competency) {
            $parent = (string) ($competency['parentidnumber'] ?? '');
            $prefix = $parent !== '' ? $parent . ' / ' : '';
            $description = trim(strip_tags((string) $competency['description']));
            if (mb_strlen($description) > 80) {
                $description = mb_substr($description, 0, 77) . '...';
            }
            $choices[(string) $idnumber] = $prefix . $idnumber . ' — ' . $competency['shortname']
                . ($description !== '' ? ' — ' . $description : '');
        }

        $mform->addElement('hidden', 'cmid', $this->_customdata['cmid']);
        $mform->setType('cmid', PARAM_INT);
        $mform->addElement('hidden', 'item', $this->_customdata['item']);
        $mform->setType('item', PARAM_RAW_TRIMMED);
        $mform->addElement('hidden', 'resourcehash', $this->_customdata['resourcehash']);
        $mform->setType('resourcehash', PARAM_RAW_TRIMMED);

        $mform->addElement('autocomplete', 'competency', get_string('competency', 'local_compalign'), $choices, [
            'noselectionstring' => get_string('competency_choose', 'local_compalign'),
        ]);
        $mform->addRule('competency', get_string('required'), 'required', null, 'client');
        $mform->setType('competency', PARAM_RAW_TRIMMED);

        $mform->addElement('textarea', 'evidencetext', get_string('supportingevidence', 'local_compalign'), [
            'rows' => 4,
            'cols' => 60,
        ]);
        $mform->setType('evidencetext', PARAM_TEXT);
        $mform->addHelpButton('evidencetext', 'supportingevidence', 'local_compalign');

        $mform->addElement('textarea', 'commenttext', get_string('commentreason', 'local_compalign'), [
            'rows' => 3,
            'cols' => 60,
        ]);
        $mform->setType('commenttext', PARAM_TEXT);

        $this->add_action_buttons(true, get_string('addcompetency', 'local_compalign'));
    }

    /**
     * Server-side checks. JavaScript is not required.
     *
     * @param array $data Submitted data.
     * @param array $files Uploaded files. None are accepted.
     * @return array Errors by field name.
     */
    public function validation($data, $files) {
        $errors = parent::validation($data, $files);
        $manager = new manual_relationship();
        $codes = $manager->find_errors(
            $this->_customdata['catalogue'],
            (string) ($data['competency'] ?? ''),
            (string) ($data['commenttext'] ?? ''),
            (string) ($data['evidencetext'] ?? ''),
            $this->_customdata['text'],
            (string) ($data['resourcehash'] ?? ''),
            (string) $this->_customdata['resourcehash'],
            $this->_customdata['active']
        );
        foreach ($codes as $code) {
            $field = match ($code) {
                'comment_too_long' => 'commenttext',
                'evidence_too_long', 'evidence_not_in_source', 'evidence_unverified' => 'evidencetext',
                'resource_changed' => 'resourcehash',
                default => 'competency',
            };
            $errors[$field] = error_messages::for_code($code);
        }

        return $errors;
    }
}
