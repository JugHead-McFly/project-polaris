-- Project Polaris PostgreSQL tenant-isolation rehearsal.
-- Run only in development or staging. All synthetic rows are deleted.

BEGIN;

DELETE FROM profiles
WHERE user_id IN (
    '11111111-1111-4111-8111-111111111111'::uuid,
    '22222222-2222-4222-8222-222222222222'::uuid
);

SET LOCAL ROLE polaris_app;

SELECT set_config(
    'app.current_user_id',
    '11111111-1111-4111-8111-111111111111',
    true
);

INSERT INTO profiles (
    user_id,
    display_name,
    onboarding_state,
    created_at,
    updated_at
) VALUES (
    '11111111-1111-4111-8111-111111111111',
    'RLS Test Alice',
    'testing',
    now(),
    now()
);

INSERT INTO observatories (
    id,
    user_id,
    name,
    latitude,
    longitude,
    coordinates_are_approximate,
    elevation_m,
    timezone_name,
    bortle_class,
    created_at,
    updated_at
) VALUES (
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    '11111111-1111-4111-8111-111111111111',
    'RLS Test Alice Observatory',
    33.25,
    -111.75,
    true,
    390,
    'America/Phoenix',
    6,
    now(),
    now()
);

SELECT set_config(
    'app.current_user_id',
    '22222222-2222-4222-8222-222222222222',
    true
);

INSERT INTO profiles (
    user_id,
    display_name,
    onboarding_state,
    created_at,
    updated_at
) VALUES (
    '22222222-2222-4222-8222-222222222222',
    'RLS Test Bob',
    'testing',
    now(),
    now()
);

INSERT INTO observatories (
    id,
    user_id,
    name,
    latitude,
    longitude,
    coordinates_are_approximate,
    elevation_m,
    timezone_name,
    bortle_class,
    created_at,
    updated_at
) VALUES (
    'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    '22222222-2222-4222-8222-222222222222',
    'RLS Test Bob Observatory',
    34.54,
    -112.47,
    true,
    1630,
    'America/Phoenix',
    4,
    now(),
    now()
);

DO $polaris_test$
DECLARE
    visible_count integer;
    affected_count integer;
BEGIN
    SELECT count(*) INTO visible_count FROM profiles;
    IF visible_count <> 1 THEN
        RAISE EXCEPTION
            'Bob profile list exposed % rows instead of 1',
            visible_count;
    END IF;

    SELECT count(*) INTO visible_count
    FROM observatories
    WHERE id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
    IF visible_count <> 0 THEN
        RAISE EXCEPTION 'Bob directly read Alice observatory';
    END IF;

    UPDATE observatories
    SET name = 'RLS Test Stolen Observatory'
    WHERE id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
    GET DIAGNOSTICS affected_count = ROW_COUNT;
    IF affected_count <> 0 THEN
        RAISE EXCEPTION 'Bob updated Alice observatory';
    END IF;

    DELETE FROM observatories
    WHERE id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
    GET DIAGNOSTICS affected_count = ROW_COUNT;
    IF affected_count <> 0 THEN
        RAISE EXCEPTION 'Bob deleted Alice observatory';
    END IF;

    BEGIN
        INSERT INTO observatories (
            id,
            user_id,
            name,
            latitude,
            longitude,
            coordinates_are_approximate,
            timezone_name,
            created_at,
            updated_at
        ) VALUES (
            'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
            '11111111-1111-4111-8111-111111111111',
            'RLS Test Forged Observatory',
            0,
            0,
            true,
            'Etc/UTC',
            now(),
            now()
        );
        RAISE EXCEPTION 'Bob forged Alice ownership';
    EXCEPTION
        WHEN insufficient_privilege THEN
            NULL;
    END;
END
$polaris_test$;

COMMIT;

BEGIN;

SET LOCAL ROLE polaris_app;

DO $polaris_test$
DECLARE
    retained_identity text;
    visible_count integer;
BEGIN
    retained_identity := current_setting(
        'app.current_user_id',
        true
    );
    IF coalesce(retained_identity, '') <> '' THEN
        RAISE EXCEPTION
            'Prior transaction identity was retained: %',
            retained_identity;
    END IF;

    SELECT count(*) INTO visible_count FROM profiles;
    IF visible_count <> 0 THEN
        RAISE EXCEPTION
            'Missing identity exposed % profile rows',
            visible_count;
    END IF;

    BEGIN
        INSERT INTO profiles (
            user_id,
            display_name,
            onboarding_state,
            created_at,
            updated_at
        ) VALUES (
            '33333333-3333-4333-8333-333333333333',
            'RLS Test Missing Identity',
            'testing',
            now(),
            now()
        );
        RAISE EXCEPTION 'Missing identity inserted a profile';
    EXCEPTION
        WHEN insufficient_privilege THEN
            NULL;
    END;
END
$polaris_test$;

ROLLBACK;

BEGIN;

DELETE FROM profiles
WHERE user_id IN (
    '11111111-1111-4111-8111-111111111111'::uuid,
    '22222222-2222-4222-8222-222222222222'::uuid,
    '33333333-3333-4333-8333-333333333333'::uuid
);

COMMIT;

SELECT json_build_object(
    'passed',
    true,
    'revision',
    (SELECT version_num FROM alembic_version),
    'role_is_superuser',
    (SELECT rolsuper FROM pg_roles WHERE rolname = 'polaris_app'),
    'role_bypasses_rls',
    (SELECT rolbypassrls FROM pg_roles WHERE rolname = 'polaris_app'),
    'hosted_table_access',
    has_table_privilege('polaris_app', 'profiles', 'SELECT'),
    'local_capture_access',
    has_table_privilege('polaris_app', 'captures', 'SELECT'),
    'synthetic_rows_remaining',
    (
        SELECT count(*)
        FROM profiles
        WHERE user_id IN (
            '11111111-1111-4111-8111-111111111111'::uuid,
            '22222222-2222-4222-8222-222222222222'::uuid,
            '33333333-3333-4333-8333-333333333333'::uuid
        )
    )
) AS tenant_isolation_verification;
