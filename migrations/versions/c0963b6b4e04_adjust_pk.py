"""Adjust PK

Revision ID: c0963b6b4e04
Revises: 
Create Date: 2023-09-26 22:50:26.036152

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c0963b6b4e04'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('station_detail',
    sa.Column('id', sa.String(length=128), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('short_name', sa.String(length=128), nullable=False),
    sa.Column('lat', sa.String(length=128), nullable=False),
    sa.Column('lon', sa.String(length=128), nullable=False),
    sa.Column('region_id', sa.String(length=128), nullable=False),
    sa.Column('capacity', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('station_status',
    sa.Column('id', sa.String(length=128), nullable=False),
    sa.Column('last_reported', sa.TIMESTAMP(), nullable=False),
    sa.Column('bikes_available', sa.Integer(), nullable=False),
    sa.Column('docks_available', sa.Integer(), nullable=False),
    sa.Column('is_installed', sa.Integer(), nullable=False),
    sa.Column('is_renting', sa.Integer(), nullable=False),
    sa.Column('is_returning', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id', 'last_reported')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('station_status')
    op.drop_table('station_detail')
    # ### end Alembic commands ###
