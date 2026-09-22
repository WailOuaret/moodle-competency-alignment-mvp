COPY (
    SELECT
        cc.id AS course_competency_link_id,
        course.id AS course_id,
        course.shortname AS course_shortname,
        course.fullname AS course_fullname,
        competency.id AS competency_id,
        competency.idnumber AS competency_idnumber,
        competency.shortname AS competency_name,
        cc.ruleoutcome,
        cc.sortorder,
        cc.timecreated,
        cc.timemodified
    FROM m_competency_coursecomp cc
    JOIN m_course course
      ON course.id = cc.courseid
    JOIN m_competency competency
      ON competency.id = cc.competencyid
    JOIN m_competency_framework framework
      ON framework.id = competency.competencyframeworkid
    WHERE framework.idnumber = 'UTC_GI_MVP_2026'
      AND course.shortname IN ('MVP-SW', 'MVP-DATA')
    ORDER BY course.id, cc.sortorder, competency.idnumber
) TO STDOUT WITH (
    FORMAT CSV,
    HEADER TRUE,
    ENCODING 'UTF8'
);
