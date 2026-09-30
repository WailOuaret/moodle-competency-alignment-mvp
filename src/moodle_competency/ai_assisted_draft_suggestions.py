"""Draft suggestions for assisted annotation review.

These are NOT independent gold labels. A researcher must confirm or
edit each row before any human_* field is filled.
"""

from __future__ import annotations


def draft_suggestions() -> dict[str, dict]:
    return {
        "page:1#f001": {
            "competency_ids": ["GI_C1_1", "GI_C1_2"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Different programming paradigms, such as object-oriented, procedural, functional, and event-driven programming, may be selected depending on the problem.",
                "Testing and verification are performed before deployment to identify defects and confirm that the software satisfies its requirements.",
            ],
            "reasoning": "The paragraph teaches software requirements, design, programming paradigms, performance, and deployment (GI_C1_1). A separate sentence independently teaches testing and verification against requirements (GI_C1_2).",
        },
        "page:1#f002": {
            "competency_ids": ["GI_C1_1"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Deployment is the process of preparing and releasing the software into a production environment.",
            ],
            "reasoning": "The fragment explains deployment, packaging, installation, and maintenance as part of delivering software. That is the child competency for software development and production release, not a separate quality-engineering lesson.",
        },
        "page:2#f001": {
            "competency_ids": ["GI_C1_3"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "This page explains user-centered design, interface prototyping, usability, accessibility, ergonomics, mobile interfaces, and user experience evaluation.",
            ],
            "reasoning": "The paragraph is a direct HCI/UX lesson: users, tasks, context, prototyping, and user-experience criteria. GI_C1_3 is the matching child competency.",
        },
        "page:2#f002": {
            "competency_ids": ["GI_C1_3"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Mobile, virtual-reality, and augmented-reality interfaces also require careful attention to screen size, interaction methods, orientation, movement, safety, and user fatigue.",
            ],
            "reasoning": "Accessibility, ergonomics, usability testing, and mobile/VR/AR interaction are the HCI/UX child competency, not general software construction.",
        },
        "page:3#f001": {
            "competency_ids": ["GI_C1_4"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "A distributed system is a collection of independent computers or software services that communicate through a network and work together as one system.",
            ],
            "reasoning": "The fragment teaches distributed applications, concurrency, and service communication (queues, RPC, web APIs, SOA). That is distributed software and scalability, not a hardware-network architecture lesson.",
        },
        "page:3#f002": {
            "competency_ids": ["GI_C1_4"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Scalability is the ability of a system to continue operating efficiently as the number of users, requests, or stored records increases.",
            ],
            "reasoning": "Horizontal/vertical scaling, load balancing, caching, replication, and partial-failure handling are the scalability side of distributed software.",
        },
        "page:3#f003": {
            "competency_ids": ["GI_C2_3", "GI_C1_4"],
            "no_competency": False,
            "ambiguous": True,
            "ambiguity_reason": "The paragraph teaches security controls, but it is the closing wrap-up of a distributed-systems page, so both cybersecurity and distributed-software readings are defensible.",
            "evidence": [
                "Authentication, authorization, encryption, secure communication, logging, and protection against malicious requests help reduce distributed-system risks.",
                "A successful distributed system balances concurrency, scalability, performance, availability, fault tolerance, consistency, and security.",
            ],
            "reasoning": "The first sentence is a cybersecurity controls lesson (GI_C2_3). The second sentence restates the whole distributed-system trade-off set (GI_C1_4). Both are independently present.",
        },
        "page:4#f001": {
            "competency_ids": ["GI_C2_1"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Hardware architecture includes processors, memory, storage devices, buses, sensors, actuators, and input-output components.",
            ],
            "reasoning": "The paragraph explains how hardware and software components, operating systems, energy, and resource limits are organized. That is GI_C2_1 rather than a networking or security child.",
        },
        "page:4#f002": {
            "competency_ids": ["GI_C2_2", "GI_C2_3"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Local networks, wide-area networks, cloud platforms, fog computing, and Internet of Things systems connect devices and distribute processing across several locations.",
                "Cybersecurity protects systems, networks, applications, and data against unauthorized access, disruption, modification, and destruction.",
            ],
            "reasoning": "The first half independently teaches communicating architectures (networks, cloud, fog, IoT). The second half independently teaches risk analysis, cybersecurity, and cryptography.",
        },
        "page:4#f003": {
            "competency_ids": ["GI_C2_3"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Secure architectures also require intrusion detection, monitoring, logging, software updates, backup systems, access control, network segmentation, and incident-response procedures.",
            ],
            "reasoning": "Authentication, authorization, intrusion detection, and cyber-resilience are the safe-architecture / cybersecurity child competency.",
        },
        "quiz_question:1:1#f001": {
            "competency_ids": ["GI_C1_1"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "What should normally be done first when developing a software system? Answer options: Understand user needs and define software requirements",
            ],
            "reasoning": "Answering requires knowing that software development starts from user needs and requirements, which belongs to GI_C1_1.",
        },
        "quiz_question:1:3#f001": {
            "competency_ids": ["GI_C1_2"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "What is the main purpose of software testing? Answer options: Identify defects and verify that requirements are satisfied",
            ],
            "reasoning": "The student must identify verification/validation as the purpose of testing, which is the software-quality child competency.",
        },
        "quiz_question:1:4#f001": {
            "competency_ids": ["GI_C1_3"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Which activity is an example of user-centred interface design? Answer options: Testing a prototype with representative users",
            ],
            "reasoning": "The item tests user-centred prototyping with representative users, which is HCI/UX.",
        },
        "quiz_question:1:5#f001": {
            "competency_ids": ["GI_C1_4"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "What does horizontal scaling mean in a distributed system? Answer options: Adding more machines to distribute the workload",
            ],
            "reasoning": "The student must apply the meaning of horizontal scaling in a distributed system, which is GI_C1_4.",
        },
        "quiz_question:1:6#f001": {
            "competency_ids": ["GI_C2_3"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "What is the purpose of cybersecurity risk analysis? Answer options: Identify assets, threats, vulnerabilities, likelihood, and potential impact",
            ],
            "reasoning": "The question is a direct cybersecurity risk-analysis item.",
        },
        "quiz_question:1:7#f001": {
            "competency_ids": ["GI_C1_2"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Which practice contributes most directly to maintaining software quality? Answer options: Using code reviews, automated testing, clear standards, and continuous maintenance",
            ],
            "reasoning": "The student must recognise quality-assurance practices (reviews, testing, standards), which is GI_C1_2.",
        },
        "page:5#f001": {
            "competency_ids": ["GI_C3_1"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "An ontology defines the concepts of a domain and the relationships between those concepts.",
            ],
            "reasoning": "Knowledge representation, formal logic, and ontologies are the KR/reasoning child competency.",
        },
        "page:5#f002": {
            "competency_ids": ["GI_C3_1"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "The Semantic Web uses structured data and shared vocabularies so that computers can interpret relationships between information from different sources.",
            ],
            "reasoning": "Ontological relationships, Semantic Web vocabularies, and automated reasoning remain GI_C3_1.",
        },
        "page:5#f003": {
            "competency_ids": ["GI_C3_1"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Ethical issues include privacy, transparency, explainability, discrimination, and the possibility of biased knowledge structures.",
            ],
            "reasoning": "The fragment discusses ethics, bias, and regulation of knowledge-representation systems, which the GI_C3_1 description already includes.",
        },
        "page:6#f001": {
            "competency_ids": ["GI_C3_2"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Relational databases represent information using tables.",
            ],
            "reasoning": "Tables, keys, entities, and relational design are the data/databases child competency.",
        },
        "page:6#f002": {
            "competency_ids": ["GI_C3_2"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "NoSQL databases use models other than traditional relational tables.",
            ],
            "reasoning": "Normalization, ACID transactions, SQL, and NoSQL models are still database modelling and storage (GI_C3_2).",
        },
        "page:6#f003": {
            "competency_ids": ["GI_C3_2"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "The choice between relational and NoSQL databases depends on the structure of the data, application requirements, expected workload, consistency needs, and scaling strategy.",
            ],
            "reasoning": "Key-value/document stores and the relational vs NoSQL design choice belong to GI_C3_2.",
        },
        "page:7#f001": {
            "competency_ids": ["GI_C3_2"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "A SELECT query retrieves data from one or more tables.",
            ],
            "reasoning": "SQL selection, filtering, and joins are querying relational data for decision support (GI_C3_2).",
        },
        "page:7#f002": {
            "competency_ids": ["GI_C3_2"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Decision-support systems transform stored data into information that helps users evaluate situations and choose actions.",
            ],
            "reasoning": "GROUP BY, HAVING, views, indexes, and decision-support queries remain GI_C3_2 rather than machine learning.",
        },
        "page:7#f003": {
            "competency_ids": ["GI_C3_2"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "SQL therefore supports both routine database operations and analytical tasks involving filtering, relationships, aggregation, comparison, reporting, and evidence-based decision-making.",
            ],
            "reasoning": "The fragment explains how SQL queries produce indicators for decisions. Visualization is mentioned only as a property of useful support, not as a data-science method lesson.",
        },
        "page:8#f001": {
            "competency_ids": ["GI_C3_3"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Data science combines programming, statistics, machine learning, and domain knowledge to extract useful information from data.",
            ],
            "reasoning": "The data-science workflow, statistical exploration, ML, and NLP introduction is the GI_C3_3 child competency.",
        },
        "page:8#f002": {
            "competency_ids": ["GI_C3_3"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Natural language processing enables computers to work with human language.",
            ],
            "reasoning": "Supervised/unsupervised learning, classification, evaluation metrics, and NLP tasks are GI_C3_3.",
        },
        "page:8#f003": {
            "competency_ids": ["GI_C3_3"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Embeddings represent words, sentences, documents, or competencies as numerical vectors in which semantically related items may appear close to one another.",
            ],
            "reasoning": "Embeddings, visualization of model results, and bias in ML systems are data science / NLP, not database querying.",
        },
        "page:8#f004": {
            "competency_ids": ["GI_C3_3"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "A reliable intelligent system therefore combines appropriate data, careful preprocessing, suitable models, valid evaluation, clear evidence, ethical safeguards, and human review.",
            ],
            "reasoning": "The closing paragraph still belongs to the data-science / ML pipeline rather than the broad GI_C3 parent.",
        },
        "quiz_question:2:8#f001": {
            "competency_ids": ["GI_C3_1"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "What does an ontology primarily define? Answer options: Concepts and relationships within a domain",
            ],
            "reasoning": "The student must know that an ontology defines domain concepts and relationships (GI_C3_1).",
        },
        "quiz_question:2:9#f001": {
            "competency_ids": ["GI_C3_2"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "What is the main purpose of a primary key in a relational table? Answer options: Uniquely identify each record",
            ],
            "reasoning": "Primary keys in relational tables are GI_C3_2.",
        },
        "quiz_question:2:10#f001": {
            "competency_ids": ["GI_C3_2"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Why is database normalization used? Answer options: To reduce unnecessary duplication and update problems",
            ],
            "reasoning": "Normalization to reduce duplication is relational database design (GI_C3_2).",
        },
        "quiz_question:2:11#f001": {
            "competency_ids": ["GI_C3_2"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "Which SQL clause is normally used to create groups before applying functions such as COUNT or AVG? Answer options: GROUP BY",
            ],
            "reasoning": "GROUP BY before COUNT/AVG is SQL querying (GI_C3_2).",
        },
        "quiz_question:2:12#f001": {
            "competency_ids": ["GI_C3_3"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "What distinguishes supervised machine learning? Answer options: The model learns from examples containing known labels or target values",
            ],
            "reasoning": "Supervised learning from labelled examples is GI_C3_3.",
        },
        "quiz_question:2:13#f001": {
            "competency_ids": ["GI_C3_3"],
            "no_competency": False,
            "ambiguous": False,
            "ambiguity_reason": "",
            "evidence": [
                "What is the purpose of an embedding in natural language processing? Answer options: Represent text as numerical vectors that capture semantic information",
            ],
            "reasoning": "NLP embeddings as semantic vectors are GI_C3_3.",
        },
    }
