COPY (
    WITH resolved_questions AS (
        SELECT
            c.id AS course_id,
            c.shortname AS course_shortname,
            qz.id AS quiz_id,
            qz.name AS quiz_name,
            qs.id AS quiz_slot_id,
            qs.slot,
            qs.displaynumber,
            qs.maxmark,
            qr.questionbankentryid,
            qv.id AS question_version_id,
            qv.version AS question_version,
            qv.status AS question_version_status,
            qv.questionid
        FROM m_quiz qz
        JOIN m_course c
          ON c.id = qz.course
        JOIN m_quiz_slots qs
          ON qs.quizid = qz.id
        JOIN m_question_references qr
          ON qr.component = 'mod_quiz'
         AND qr.questionarea = 'slot'
         AND qr.itemid = qs.id
        JOIN LATERAL (
            SELECT version_record.*
            FROM m_question_versions version_record
            WHERE version_record.questionbankentryid =
                  qr.questionbankentryid
              AND (
                    qr.version IS NULL
                 OR qr.version = 0
                 OR version_record.version = qr.version
              )
            ORDER BY version_record.version DESC,
                     version_record.id DESC
            LIMIT 1
        ) qv ON TRUE
        WHERE qz.id IN (1, 2)
    )
    SELECT
        rq.course_id,
        rq.course_shortname,
        rq.quiz_id,
        rq.quiz_name,
        rq.quiz_slot_id,
        rq.slot,
        rq.displaynumber,
        rq.maxmark,
        rq.questionbankentryid AS question_bank_entry_id,
        rq.question_version_id,
        rq.question_version,
        rq.question_version_status,
        q.id AS question_id,
        q.name AS question_name,
        q.qtype AS question_type,
        q.questiontext AS question_text,
        q.questiontextformat AS question_text_format,
        q.generalfeedback AS general_feedback,
        q.defaultmark AS default_mark,
        a.id AS answer_id,
        a.answer AS answer_text,
        a.answerformat AS answer_format,
        a.fraction AS answer_fraction,
        a.feedback AS answer_feedback,
        a.feedbackformat AS feedback_format
    FROM resolved_questions rq
    JOIN m_question q
      ON q.id = rq.questionid
    LEFT JOIN m_question_answers a
      ON a.question = q.id
    ORDER BY
        rq.quiz_id,
        rq.slot,
        a.id
) TO STDOUT WITH (
    FORMAT CSV,
    HEADER TRUE,
    ENCODING 'UTF8'
);
