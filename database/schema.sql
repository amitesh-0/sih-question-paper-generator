-- =====================================================================
-- AI-Based Learning-Outcome-Aligned Question Paper Generator (SIH-2026)
-- Database Schema — SQL DDL (PostgreSQL)
-- =====================================================================

-- ---------------------------------------------------------------------
-- ZONE I: IDENTITY, MULTI-TENANCY & INSTITUTIONAL GOVERNANCE
-- ---------------------------------------------------------------------

CREATE TABLE institutions (
    institution_id       SERIAL PRIMARY KEY,
    name                 VARCHAR(150) NOT NULL,
    university_code      VARCHAR(50) UNIQUE,
    encryption_key_shard VARCHAR(255) NULL,
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE departments (
    department_id  SERIAL PRIMARY KEY,
    institution_id INT NOT NULL,
    name           VARCHAR(100) NOT NULL,
    CONSTRAINT fk_dept_inst FOREIGN KEY (institution_id) REFERENCES institutions(institution_id) ON DELETE RESTRICT
);

CREATE TABLE roles (
    role_id       SERIAL PRIMARY KEY,
    role_name     VARCHAR(50) NOT NULL CHECK (role_name IN ('Paper_Setter','HOD','Board_of_Examiners','Controller_of_Examinations','Dean','System_Admin')),
    approval_rank INT NULL,
    office_title  VARCHAR(100) NOT NULL
);

CREATE TABLE users (
    user_id                 SERIAL PRIMARY KEY,
    employee_id             VARCHAR(20)  NOT NULL UNIQUE,
    name                    VARCHAR(150) NOT NULL,
    email                   VARCHAR(150) NOT NULL UNIQUE,
    password_hash           VARCHAR(255) NOT NULL,
    department_id           INT NOT NULL,
    role_id                 INT NOT NULL,
    designation             VARCHAR(100) NULL,
    digital_signature_key   VARCHAR(255) NULL,
    is_active               BOOLEAN DEFAULT TRUE,
    last_login_at           TIMESTAMP NULL,
    failed_login_attempts   INT NOT NULL DEFAULT 0,
    account_locked_until    TIMESTAMP NULL,
    password_updated_at     TIMESTAMP NULL,
    created_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_department FOREIGN KEY (department_id) REFERENCES departments(department_id) ON DELETE RESTRICT,
    CONSTRAINT fk_users_role       FOREIGN KEY (role_id)       REFERENCES roles(role_id) ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------
-- ZONE II: ACADEMIC STRUCTURE & RAG EMBEDDINGS
-- ---------------------------------------------------------------------

CREATE TABLE courses (
    course_id       SERIAL PRIMARY KEY,
    department_id   INT NOT NULL,
    course_code     VARCHAR(20)  NOT NULL UNIQUE,
    course_name     VARCHAR(150) NOT NULL,
    semester        INT NOT NULL,
    course_owner_id INT NOT NULL,
    CONSTRAINT fk_courses_department FOREIGN KEY (department_id) REFERENCES departments(department_id) ON DELETE RESTRICT,
    CONSTRAINT fk_courses_owner      FOREIGN KEY (course_owner_id) REFERENCES users(user_id) ON DELETE RESTRICT
);

CREATE TABLE syllabus (
    syllabus_id         SERIAL PRIMARY KEY,
    course_id           INT NOT NULL,
    academic_year       VARCHAR(9)  NOT NULL,
    version             VARCHAR(10) NOT NULL,
    approved_by         INT NOT NULL,
    ordinance_reference VARCHAR(50) NULL,
    original_filename   VARCHAR(255) NULL,
    raw_extracted_text  TEXT NULL,
    CONSTRAINT fk_syllabus_course   FOREIGN KEY (course_id)   REFERENCES courses(course_id) ON DELETE RESTRICT,
    CONSTRAINT fk_syllabus_approver FOREIGN KEY (approved_by) REFERENCES users(user_id) ON DELETE RESTRICT
);

CREATE TABLE syllabus_units (
    unit_id               SERIAL PRIMARY KEY,
    syllabus_id           INT NOT NULL,
    unit_name             VARCHAR(150) NOT NULL,
    unit_number           INT NOT NULL,
    weightage_percent     DECIMAL(5,2) NOT NULL,
    applicable_exam_types JSONB NULL,
    CONSTRAINT fk_units_syllabus FOREIGN KEY (syllabus_id) REFERENCES syllabus(syllabus_id) ON DELETE RESTRICT
);

CREATE TABLE topics (
    topic_id   SERIAL PRIMARY KEY,
    unit_id    INT NOT NULL,
    topic_name VARCHAR(150) NOT NULL,
    CONSTRAINT fk_topics_unit FOREIGN KEY (unit_id) REFERENCES syllabus_units(unit_id) ON DELETE RESTRICT
);

CREATE TABLE syllabus_embeddings (
    chunk_id        SERIAL PRIMARY KEY,
    topic_id        INT NOT NULL,
    chunk_text      TEXT NOT NULL,
    vector_data     JSONB NOT NULL, 
    CONSTRAINT fk_embed_topic FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE RESTRICT
);

CREATE TABLE course_outcomes (
    co_id       SERIAL PRIMARY KEY,
    course_id   INT NOT NULL,
    co_code     VARCHAR(10) NOT NULL,
    description TEXT NOT NULL,
    po_mapping  JSONB NULL,
    CONSTRAINT fk_co_course FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE RESTRICT
);

CREATE TABLE bloom_levels (
    bloom_id    SERIAL PRIMARY KEY,
    level_name  VARCHAR(20) NOT NULL,        
    level_order INT NOT NULL
);

CREATE TABLE difficulty_levels (
    difficulty_id             SERIAL PRIMARY KEY,
    label                     VARCHAR(10) NOT NULL,   
    default_weightage_percent DECIMAL(5,2) NOT NULL
);

CREATE TABLE exam_types (
    exam_type_id             SERIAL PRIMARY KEY,
    name                     VARCHAR(30) NOT NULL UNIQUE, 
    default_duration_minutes INT NOT NULL,
    default_total_marks      DECIMAL(6,2) NOT NULL,
    syllabus_scope           VARCHAR(20) NOT NULL CHECK (syllabus_scope IN ('Partial','Full')),
    governing_regulation     VARCHAR(100) NULL
);

CREATE TABLE question_types (
    question_type_id SERIAL PRIMARY KEY,
    name             VARCHAR(30) NOT NULL UNIQUE,   
    default_marks    DECIMAL(5,2) NOT NULL
);

-- ---------------------------------------------------------------------
-- ZONE III: QUESTION BANK (WITH AI METADATA & SOFT DELETES)
-- ---------------------------------------------------------------------

CREATE TABLE questions (
    question_id                    SERIAL PRIMARY KEY,
    topic_id                       INT NOT NULL,
    co_id                          INT NOT NULL,
    bloom_id                       INT NOT NULL,      
    difficulty_id                  INT NOT NULL,      
    question_type_id               INT NOT NULL,
    
    question_text                  TEXT NOT NULL,
    options_json                   JSONB NULL,
    model_answer                   TEXT NULL,
    
    expected_answer_length         VARCHAR(50) NOT NULL CHECK (expected_answer_length IN ('One-Word', 'One-Sentence', 'Short-Paragraph', 'Multi-Paragraph', 'Essay/Derivation', 'Diagram-Only')),
    
    source                         VARCHAR(50) NOT NULL CHECK (source IN ('AI-Generated','Faculty-Authored','Bank-Imported')),
    ai_cognitive_validation_score  DECIMAL(3,2) NULL, 
    hallucination_flag             BOOLEAN DEFAULT FALSE,
    translations_json              JSONB NULL, 
    
    created_by                     INT NOT NULL,
    status                         VARCHAR(50) NOT NULL DEFAULT 'Draft' CHECK (status IN ('Draft','Approved','Rejected','Archived')),
    created_at                     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                     TIMESTAMP NULL,
    deleted_at                     TIMESTAMP NULL,
    
    CONSTRAINT fk_q_topic         FOREIGN KEY (topic_id)         REFERENCES topics(topic_id) ON DELETE RESTRICT,
    CONSTRAINT fk_q_co            FOREIGN KEY (co_id)            REFERENCES course_outcomes(co_id) ON DELETE RESTRICT,
    CONSTRAINT fk_q_bloom         FOREIGN KEY (bloom_id)         REFERENCES bloom_levels(bloom_id) ON DELETE RESTRICT,
    CONSTRAINT fk_q_difficulty    FOREIGN KEY (difficulty_id)    REFERENCES difficulty_levels(difficulty_id) ON DELETE RESTRICT,
    CONSTRAINT fk_q_type          FOREIGN KEY (question_type_id) REFERENCES question_types(question_type_id) ON DELETE RESTRICT,
    CONSTRAINT fk_q_created_by    FOREIGN KEY (created_by)       REFERENCES users(user_id) ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------
-- ZONE IV: MILP SOLVER CONSTRAINTS (BLUEPRINTS)
-- ---------------------------------------------------------------------

CREATE TABLE paper_blueprints (
    blueprint_id            SERIAL PRIMARY KEY,
    course_id               INT NOT NULL,
    syllabus_id             INT NOT NULL,
    exam_type_id            INT NOT NULL,
    total_marks             DECIMAL(6,2) NOT NULL,
    duration_minutes        INT NOT NULL,
    number_of_sets_required INT NOT NULL DEFAULT 1,
    regulatory_reference    VARCHAR(100) NULL,
    created_by              INT NOT NULL,     
    requested_by_admin      INT NULL,         
    created_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at              TIMESTAMP NULL,
    CONSTRAINT fk_bp_course    FOREIGN KEY (course_id)   REFERENCES courses(course_id) ON DELETE RESTRICT,
    CONSTRAINT fk_bp_syllabus  FOREIGN KEY (syllabus_id) REFERENCES syllabus(syllabus_id) ON DELETE RESTRICT,
    CONSTRAINT fk_bp_examtype  FOREIGN KEY (exam_type_id) REFERENCES exam_types(exam_type_id) ON DELETE RESTRICT,
    CONSTRAINT fk_bp_created_by FOREIGN KEY (created_by)   REFERENCES users(user_id) ON DELETE RESTRICT,
    CONSTRAINT fk_bp_admin     FOREIGN KEY (requested_by_admin) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE blueprint_unit_weightage (
    id             SERIAL PRIMARY KEY,
    blueprint_id   INT NOT NULL,
    unit_id        INT NOT NULL,
    target_marks   DECIMAL(5,2) NOT NULL,
    CONSTRAINT fk_buw_blueprint FOREIGN KEY (blueprint_id) REFERENCES paper_blueprints(blueprint_id) ON DELETE RESTRICT,
    CONSTRAINT fk_buw_unit      FOREIGN KEY (unit_id)      REFERENCES syllabus_units(unit_id) ON DELETE RESTRICT
);

CREATE TABLE blueprint_difficulty_distribution (
    id             SERIAL PRIMARY KEY,
    blueprint_id   INT NOT NULL,
    difficulty_id  INT NOT NULL,
    target_percent DECIMAL(5,2) NOT NULL,
    CONSTRAINT fk_bdd_blueprint  FOREIGN KEY (blueprint_id)  REFERENCES paper_blueprints(blueprint_id) ON DELETE RESTRICT,
    CONSTRAINT fk_bdd_difficulty FOREIGN KEY (difficulty_id) REFERENCES difficulty_levels(difficulty_id) ON DELETE RESTRICT
);

CREATE TABLE blueprint_question_type_distribution (
    id                 SERIAL PRIMARY KEY,
    blueprint_id       INT NOT NULL,
    question_type_id   INT NOT NULL,
    target_count       INT NOT NULL,
    CONSTRAINT fk_bqtd_blueprint FOREIGN KEY (blueprint_id)     REFERENCES paper_blueprints(blueprint_id) ON DELETE RESTRICT,
    CONSTRAINT fk_bqtd_qtype     FOREIGN KEY (question_type_id) REFERENCES question_types(question_type_id) ON DELETE RESTRICT
);

CREATE TABLE blueprint_co_coverage (
    id            SERIAL PRIMARY KEY,
    blueprint_id  INT NOT NULL,
    co_id         INT NOT NULL,
    min_questions INT NOT NULL,
    CONSTRAINT fk_bcc_blueprint FOREIGN KEY (blueprint_id) REFERENCES paper_blueprints(blueprint_id) ON DELETE RESTRICT,
    CONSTRAINT fk_bcc_co        FOREIGN KEY (co_id)        REFERENCES course_outcomes(co_id) ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------
-- ZONE V: GENERATION & SECURE PAPER STORAGE
-- ---------------------------------------------------------------------

CREATE TABLE generation_batches (
    generation_batch_id   SERIAL PRIMARY KEY,
    blueprint_id          INT NOT NULL,
    triggered_by          INT NOT NULL,     
    model_used            VARCHAR(50) NOT NULL,
    requested_set_count   INT NOT NULL,
    status                VARCHAR(50) NOT NULL CHECK (status IN ('Running','Completed','Failed')),
    triggered_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at          TIMESTAMP NULL,
    CONSTRAINT fk_gb_blueprint FOREIGN KEY (blueprint_id) REFERENCES paper_blueprints(blueprint_id) ON DELETE RESTRICT,
    CONSTRAINT fk_gb_admin     FOREIGN KEY (triggered_by) REFERENCES users(user_id) ON DELETE RESTRICT
);

CREATE TABLE paper_sets (
    set_id                         SERIAL PRIMARY KEY,
    blueprint_id                   INT NOT NULL,
    generation_batch_id            INT NOT NULL,
    set_label                      VARCHAR(10) NOT NULL,      
    official_paper_code            VARCHAR(30) NULL UNIQUE,   
    confidentiality_classification VARCHAR(50) NOT NULL DEFAULT 'Restricted' CHECK (confidentiality_classification IN ('Restricted','Confidential','Top Secret')),
    status                         VARCHAR(50) NOT NULL DEFAULT 'Generated' CHECK (status IN ('Generated','Under Paper Setter Review','Under HOD Review','Under Board Review','Under CoE Review','Under Dean Review','Approved','Rejected','Published','Archived')),
    
    encrypted_compiled_paper       BYTEA NULL,
    decryption_time_lock           TIMESTAMP NULL,
    
    generated_at                   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at                   TIMESTAMP NULL,
    published_by                   INT NULL,
    deleted_at                     TIMESTAMP NULL,
    
    CONSTRAINT fk_ps_blueprint FOREIGN KEY (blueprint_id)        REFERENCES paper_blueprints(blueprint_id) ON DELETE RESTRICT,
    CONSTRAINT fk_ps_batch     FOREIGN KEY (generation_batch_id) REFERENCES generation_batches(generation_batch_id) ON DELETE RESTRICT,
    CONSTRAINT fk_ps_publisher FOREIGN KEY (published_by)        REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE set_questions (
    id             SERIAL PRIMARY KEY,
    set_id         INT NOT NULL,
    question_id    INT NOT NULL,
    sequence_no    INT NOT NULL,
    marks_allotted DECIMAL(5,2) NOT NULL,
    section        VARCHAR(10) NULL,
    is_edited      BOOLEAN DEFAULT FALSE,
    CONSTRAINT fk_sq_set      FOREIGN KEY (set_id)      REFERENCES paper_sets(set_id) ON DELETE RESTRICT,
    CONSTRAINT fk_sq_question FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------
-- ZONE VI: APPROVAL WORKFLOW & AUDIT TRAIL
-- ---------------------------------------------------------------------

CREATE TABLE approval_stages (
    stage_id         SERIAL PRIMARY KEY,
    stage_name       VARCHAR(50) NOT NULL,
    stage_order      INT NOT NULL UNIQUE,      
    required_role_id INT NOT NULL,
    CONSTRAINT fk_as_role FOREIGN KEY (required_role_id) REFERENCES roles(role_id) ON DELETE RESTRICT
);

CREATE TABLE set_approvals (
    approval_id            SERIAL PRIMARY KEY,
    set_id                 INT NOT NULL,
    stage_id               INT NOT NULL,
    reviewer_id            INT NOT NULL,
    decision               VARCHAR(50) NOT NULL CHECK (decision IN ('Approved','Changes Requested','Rejected')),
    comments               TEXT NULL,
    digital_signature_hash VARCHAR(255) NULL,   
    decided_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sa_set      FOREIGN KEY (set_id)      REFERENCES paper_sets(set_id) ON DELETE RESTRICT,
    CONSTRAINT fk_sa_stage    FOREIGN KEY (stage_id)    REFERENCES approval_stages(stage_id) ON DELETE RESTRICT,
    CONSTRAINT fk_sa_reviewer FOREIGN KEY (reviewer_id) REFERENCES users(user_id) ON DELETE RESTRICT
);

CREATE TABLE set_edit_log (
    edit_id         SERIAL PRIMARY KEY,
    set_id          INT NOT NULL,
    question_id     INT NULL,
    edited_by       INT NOT NULL,
    edited_at_stage INT NOT NULL,
    field_changed   VARCHAR(50) NOT NULL,
    old_value       TEXT NULL,
    new_value       TEXT NULL,
    edited_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sel_set      FOREIGN KEY (set_id)          REFERENCES paper_sets(set_id) ON DELETE RESTRICT,
    CONSTRAINT fk_sel_question FOREIGN KEY (question_id)     REFERENCES questions(question_id) ON DELETE SET NULL,
    CONSTRAINT fk_sel_user     FOREIGN KEY (edited_by)       REFERENCES users(user_id) ON DELETE RESTRICT,
    CONSTRAINT fk_sel_stage    FOREIGN KEY (edited_at_stage) REFERENCES approval_stages(stage_id) ON DELETE RESTRICT
);

CREATE TABLE set_versions (
    version_id     SERIAL PRIMARY KEY,
    set_id         INT NOT NULL,
    version_number INT NOT NULL,
    snapshot_json  JSONB NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sv_set FOREIGN KEY (set_id) REFERENCES paper_sets(set_id) ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------
-- ZONE VII: SECURITY & CHAIN OF CUSTODY
-- ---------------------------------------------------------------------

CREATE TABLE custody_log (
    custody_id         SERIAL PRIMARY KEY,
    set_id             INT NOT NULL,
    event_type         VARCHAR(50) NOT NULL CHECK (event_type IN ('Viewed','Downloaded','Printed','Distributed','Sealed')),
    performed_by       INT NOT NULL,
    location_or_center VARCHAR(100) NULL,
    ip_address         VARCHAR(45) NULL,
    event_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cl_set  FOREIGN KEY (set_id)       REFERENCES paper_sets(set_id) ON DELETE RESTRICT,
    CONSTRAINT fk_cl_user FOREIGN KEY (performed_by) REFERENCES users(user_id) ON DELETE RESTRICT
);

CREATE TABLE access_permissions (
    id           SERIAL PRIMARY KEY,
    set_id       INT NOT NULL,
    user_id      INT NOT NULL,
    access_level VARCHAR(50) NOT NULL CHECK (access_level IN ('View','Edit','Approve','Publish')),
    granted_by   INT NOT NULL,
    granted_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at   TIMESTAMP NULL,
    CONSTRAINT fk_ap_set        FOREIGN KEY (set_id)     REFERENCES paper_sets(set_id) ON DELETE RESTRICT,
    CONSTRAINT fk_ap_user       FOREIGN KEY (user_id)    REFERENCES users(user_id) ON DELETE RESTRICT,
    CONSTRAINT fk_ap_granted_by FOREIGN KEY (granted_by) REFERENCES users(user_id) ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------
-- ZONE VIII: PERFORMANCE INDEXES (FOR MILP SOLVER & AUTH)
-- ---------------------------------------------------------------------

CREATE INDEX idx_solver_candidates ON questions (co_id, topic_id, bloom_id, difficulty_id, status);
CREATE INDEX idx_users_auth ON users (email, is_active);
CREATE INDEX idx_blueprint_lookup ON paper_blueprints (course_id, exam_type_id);
CREATE INDEX idx_paper_sets_status ON paper_sets (blueprint_id, status);

-- =====================================================================
-- SEED DATA 
-- =====================================================================

INSERT INTO roles (role_name, approval_rank, office_title) VALUES
('Paper_Setter',               1, 'Professor / Course Faculty'),
('HOD',                        2, 'Head of Department'),
('Board_of_Examiners',         3, 'Moderation Committee'),
('Controller_of_Examinations', 4, 'Office of the Controller of Examinations'),
('Dean',                       5, 'Dean, Academic Affairs'),
('System_Admin',               NULL, 'Examination Cell (Technical)');

INSERT INTO approval_stages (stage_name, stage_order, required_role_id) VALUES
('Paper Setter Review',               1, 1),
('HOD Review',                        2, 2),
('Board of Examiners Review',         3, 3),
('Controller of Examinations Review', 4, 4),
('Dean Approval',                     5, 5);

INSERT INTO difficulty_levels (label, default_weightage_percent) VALUES
('Easy',   30.00),
('Medium', 50.00),
('Hard',   20.00);

INSERT INTO bloom_levels (level_name, level_order) VALUES
('Remember',    1),
('Understand',  2),
('Apply',       3),
('Analyze',     4),
('Evaluate',    5),
('Create',      6);

INSERT INTO exam_types (name, default_duration_minutes, default_total_marks, syllabus_scope) VALUES
('Mid-Sem-1', 90,  30.00, 'Partial'),
('Mid-Sem-2', 90,  30.00, 'Partial'),
('End-Sem',   180, 100.00, 'Full'),
('Quiz',      30,  10.00, 'Partial');

INSERT INTO question_types (name, default_marks) VALUES
('MCQ',                1.00),
('Short Answer',       5.00),
('Long Answer',        10.00),
('Numerical',          5.00),
('Fill-in-the-Blank',  1.00);
