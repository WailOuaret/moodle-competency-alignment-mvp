COPY (
    SELECT
        id,
        shortname,
        idnumber,
        description,
        descriptionformat,
        contextid,
        scaleid,
        scaleconfiguration,
        visible,
        taxonomies,
        timecreated,
        timemodified
    FROM m_competency_framework
    WHERE idnumber = 'UTC_GI_MVP_2026'
    ORDER BY id
) TO STDOUT WITH (
    FORMAT CSV,
    HEADER TRUE,
    ENCODING 'UTF8'
);
