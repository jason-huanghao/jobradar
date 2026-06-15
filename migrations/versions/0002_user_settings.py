"""user_settings table — per-user LLM endpoint selection

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_settings',
        sa.Column('user_email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('model', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('base_url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('api_key_env', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_email'], ['user.email'], ),
        sa.PrimaryKeyConstraint('user_email'),
    )


def downgrade() -> None:
    op.drop_table('user_settings')
