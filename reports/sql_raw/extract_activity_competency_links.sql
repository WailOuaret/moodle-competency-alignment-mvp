COPY (
    SELECT
        mc.id AS activity_competency_link_id,
        course.id AS course_id,
        course.shortname AS course_shortname,
        course.fullname AS course_fullname,
        cm.id AS course_module_id,
        module.name AS module_type,
        cm.instance AS module_instance_id,
        CASE
            WHEN module.name = 'page' THEN (
                SELECT page.name
                FROM m_page page
                WHERE page.id = cm.instance
            )
            WHEN module.name = 'quiz' THEN (
                SELECT quiz.name
                FROM m_quiz quiz
                WHERE quiz.id = cm.instance
            )
            ELSE module.name || ' instance ' || cm.instance::text
        END AS activity_name,
        competency.id AS competency_id,
        competency.idnumber AS competency_idnumber,
        competency.shortname AS competency_name,
        mc.ruleoutcome,
        mc.overridegrade,
        mc.sortorder,
        mc.timecreated,
        mc.timemodified
    FROM m_competency_modulecomp mc
    JOIN m_course_modules cm
      ON cm.id = mc.cmid
    JOIN m_course course
      ON course.id = cm.course
    JOIN m_modules module
      ON module.id = cm.module
    JOIN m_competency competency
      ON competency.id = mc.competencyid
    JOIN m_competency_framework framework
      ON framework.id = competency.competencyframeworkid
    WHERE framework.idnumber = 'UTC_GI_MVP_2026'
      AND course.shortname IN ('MVP-SW', 'MVP-DATA')
    ORDER BY
        course.id,
        cm.id,
        mc.sortorder,
        competency.idnumber
) TO STDOUT WITH (
    FORMAT CSV,
    HEADER TRUE,
    ENCODING 'UTF8'
);
