COPY (
    SELECT
        course.id AS course_id,
        course.shortname AS course_shortname,
        course.fullname AS course_fullname,
        course.enablecompletion AS course_completion_enabled,

        cm.id AS course_module_id,
        module.name AS module_type,
        cm.instance AS module_instance_id,

        COALESCE(
            page.name,
            quiz.name,
            forum.name,
            module.name || ' instance ' || cm.instance::text
        ) AS activity_name,

        cm.completion AS completion_method,
        cm.completionview AS completion_requires_view,
        cm.completiongradeitemnumber,
        cm.completionpassgrade AS completion_requires_passing_grade,
        cm.completionexpected,

        completion.id AS completion_record_id,
        completion.userid AS user_id,
        users.username,
        users.firstname,
        users.lastname,
        completion.completionstate,
        completion.overrideby,
        completion.timemodified AS completion_time_modified

    FROM m_course_modules cm

    JOIN m_course course
      ON course.id = cm.course

    JOIN m_modules module
      ON module.id = cm.module

    LEFT JOIN m_page page
      ON module.name = 'page'
     AND page.id = cm.instance

    LEFT JOIN m_quiz quiz
      ON module.name = 'quiz'
     AND quiz.id = cm.instance

    LEFT JOIN m_forum forum
      ON module.name = 'forum'
     AND forum.id = cm.instance

    LEFT JOIN m_course_modules_completion completion
      ON completion.coursemoduleid = cm.id

    LEFT JOIN m_user users
      ON users.id = completion.userid

    WHERE course.id IN (2, 3)

    ORDER BY
        course.id,
        cm.id,
        completion.userid
) TO STDOUT WITH (
    FORMAT CSV,
    HEADER TRUE,
    ENCODING 'UTF8'
);
