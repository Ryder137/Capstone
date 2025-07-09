"""create content table

Revision ID: create_content_table
Revises: 
Create Date: 2025-07-09 02:21:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_content_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'content',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_published', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('tags', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('featured_image', sa.String(), nullable=True),
        sa.Column('slug', sa.String(), unique=True, nullable=False),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('meta_title', sa.String(), nullable=True),
        sa.Column('meta_description', sa.Text(), nullable=True),
        sa.Column('view_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('published_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['auth.users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for faster lookups
    op.create_index('idx_content_slug', 'content', ['slug'], unique=True)
    op.create_index('idx_content_type', 'content', ['content_type'])
    op.create_index('idx_content_published', 'content', ['is_published'])

def downgrade():
    op.drop_table('content')
