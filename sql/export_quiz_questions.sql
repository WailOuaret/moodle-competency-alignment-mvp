COPY (
    WITH resolved_questions AS (
        SELECT
            course.id AS course_id,
            course.shortname AS course_shortname,
            course.fullname AS course_fullname,

            quiz.id AS quiz_id,
            quiz.name AS quiz_name,

            slot.id AS quiz_slot_id,
            slot.slot,
            slot.displaynumber,
            slot.maxmark,

            reference.questionbankentryid,

            version.id AS question_version_id,
            version.version AS question_version,
            version.status AS question_version_status,
            version.questionid

        FROM m_quiz quiz

        JOIN m_course course
          ON course.id = quiz.course

        JOIN m_quiz_slots slot
          ON slot.quizid = quiz.id

        JOIN m_question_references reference
          ON reference.component = 'mod_quiz'
         AND reference.questionarea = 'slot'
         AND reference.itemid = slot.id

        JOIN LATERAL (
            SELECT candidate.*
            FROM m_question_versions candidate
            WHERE candidate.questionbankentryid =
                  reference.questionbankentryid
              AND (
                    reference.version IS NULL
                 OR reference.version = 0
                 OR candidate.version = reference.version
              )
            ORDER BY
                candidate.version DESC,
                candidate.id DESC
            LIMIT 1
        ) version ON TRUE

        WHERE course.shortname IN (
            'MVP-SW',
            'MVP-DATA'
        )
    )

    SELECT
        resolved.course_id,
        resolved.course_shortname,
        resolved.course_fullname,

        resolved.quiz_id,
        resolved.quiz_name,
        resolved.quiz_slot_id,
        resolved.slot,
        resolved.displaynumber,
        resolved.maxmark,

        resolved.questionbankentryid AS question_bank_entry_id,
        resolved.question_version_id,
        resolved.question_version,
        resolved.question_version_status,

        question.id AS question_id,
        question.name AS question_name,
        question.qtype AS question_type,
        question.questiontext AS question_text,
        question.questiontextformat AS question_text_format,
        question.generalfeedback AS general_feedback,
        question.defaultmark AS default_mark,

        answer.id AS answer_id,
        answer.answer AS answer_text,
        answer.answerformat AS answer_format,
        answer.fraction AS answer_fraction,
        answer.feedback AS answer_feedback,
        answer.feedbackformat AS feedback_format

    FROM resolved_questions resolved

    JOIN m_question question
      ON question.id = resolved.questionid

    LEFT JOIN m_question_answers answer
      ON answer.question = question.id

    ORDER BY
        resolved.course_id,
        resolved.quiz_id,
        resolved.slot,
        answer.id
) TO STDOUT WITH (
    FORMAT CSV,
    HEADER TRUE,
    ENCODING 'UTF8'
);
