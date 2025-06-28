
CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    student_name TEXT,
    student_gender TEXT,
    student_gender_other TEXT,
    dob TEXT,
    email TEXT,
    phone TEXT,
    grade TEXT,
    parent_name TEXT,
    parent_contact TEXT,
    school_name TEXT,
    school_location TEXT,
    school_contact TEXT,
    teacher_name TEXT,
    teacher_contact TEXT,
    subjects TEXT,
    interests TEXT,
    accommodation_required TEXT,
    accommodation_comment TEXT,
    essay1 TEXT,
    essay2 TEXT,
    essay3 TEXT,
    optional_info TEXT,
    file_path TEXT
);

CREATE TABLE IF NOT EXISTS activities (
    id SERIAL PRIMARY KEY,
    application_id INTEGER REFERENCES applications(id) ON DELETE CASCADE,
    activity_type TEXT,
    activity_position TEXT,
    activity_org TEXT,
    activity_desc TEXT
);
