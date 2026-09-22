COPY (
    SELECT
        c.id,
        c.competencyframeworkid,
        f.shortname AS framework_name,
        f.idnumber AS framework_idnumber,
        c.shortname,
        c.idnumber,
        c.description,
        c.descriptionformat,
        c.parentid,
        parent.idnumber AS parent_idnumber,
        parent.shortname AS parent_shortname,
        c.path,
        c.sortorder,
        c.ruletype,
        c.ruleoutcome,
        c.scaleid,
        c.timecreated,
        c.timemodified
    FROM m_competency c
    JOIN m_competency_framework f
      ON f.id = c.competencyframeworkid
    LEFT JOIN m_competency parent
      ON parent.id = c.parentid
    WHERE f.idnumber = 'UTC_GI_MVP_2026'
    ORDER BY c.path, c.sortorder, c.id
) TO STDOUT WITH (
    FORMAT CSV,
    HEADER TRUE,
    ENCODING 'UTF8'
);
