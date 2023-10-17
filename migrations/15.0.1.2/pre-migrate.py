def migrate(cr, version):
    tables_and_columns = [
        (
            "alfaleads_agreement_agreement_route_line",
            "route_ref",
            "route_ref_id",
        ),
        (
            "alfaleads_agreement_agreement_route_line",
            "agreement",
            "agreement_id",
        ),
        (
            "alfaleads_agreement_agreement_process",
            "agreement",
            "agreement_id",
        ),
        (
            "alfaleads_agreement_agreement_step",
            "agreement_process",
            "agreement_process_id",
        ),
        (
            "alfaleads_agreement_agreement_task",
            "agreement_step",
            "agreement_step_id",
        ),
        (
            "alfaleads_agreement_agreement_task",
            "approver",
            "approver_id",
        ),
        (
            "alfaleads_agreement_record_agreement",
            "task",
            "task_id",
        ),
    ]

    for table, old_column, new_column in tables_and_columns:
        query = """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = %s
                        AND column_name = %s
                    ) THEN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM information_schema.columns
                            WHERE table_name = %s
                            AND column_name = %s
                        ) THEN
                            EXECUTE 'ALTER TABLE ' || %s || ' RENAME COLUMN ' || %s || ' TO ' || %s;
                        END IF;
                    END IF;
                END $$;
            """
        cr.execute(
            query, (table, old_column, table, new_column, table, old_column, new_column)
        )
