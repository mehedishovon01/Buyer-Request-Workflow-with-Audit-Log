# Phase A: Thin Slice Design Document

## 1. Stack Choice

### Frontend
- **React.js** with TypeScript
- **Material-UI** for consistent UI components
- **Redux Toolkit** for state management
- **Axios** for API calls

### Backend
- **Django REST Framework (DRF)**
  - Robust API development
  - Built-in authentication
  - Excellent ORM for database operations
  - Python's rich ecosystem

### Database
- **PostgreSQL**
  - ACID compliance
  - JSONB support for flexible data
  - Strong community and documentation

### Storage
- **AWS S3**
  - Scalable file storage
  - Cost-effective
  - High availability

## 2. Data Model

### Core Entities & Relationships
```
User (1) --- (*) Evidence
User (1) --- (*) Request (as buyer)
User (1) --- (*) Request (as factory)
Request (1) --- (*) RequestItem
Evidence (1) --- (*) EvidenceVersion
EvidenceVersion (1) --- (0..1) RequestItem
```

### Key Models

1. **User**
   - id (PK)
   - user_id
   - role (BUYER/FACTORY/ADMIN)
   - email
   - name
   - created_at
   - updated_at

2. **Evidence**
   - id (PK)
   - name
   - doc_type
   - factory (FK to User, role=FACTORY)
   - created_at
   - updated_at

3. **EvidenceVersion**
   - id (PK)
   - evidence (FK to Evidence)
   - version_number
   - notes
   - expiry_date
   - file (FileField)
   - created_at
   - created_by (FK to User)

4. **Request**
   - id (PK)
   - title
   - buyer (FK to User, role=BUYER)
   - factory (FK to User, role=FACTORY)
   - status (PENDING/IN_PROGRESS/COMPLETED/CANCELLED)
   - created_at
   - updated_at

5. **RequestItem**
   - id (PK)
   - request (FK to Request)
   - doc_type
   - status (PENDING/FULFILLED/REJECTED)
   - evidence_version (FK to EvidenceVersion, optional)
   - fulfilled_at
   - fulfilled_by (FK to User, role=FACTORY)
   - notes
   - created_at
   - updated_at

6. **AuditLog** (Referenced from users.models)
   - action (CREATE/UPDATE/DELETE)
   - object_type
   - object_id
   - actor (FK to User)
   - timestamp
   - metadata (JSON field for additional context)

## 3. Selective Disclosure (Phase A)
- **Basic RBAC** (Role-Based Access Control)
  - Admin: Full access
  - Requester: Create/view own requests
  - Worker: View assigned tasks, update status
- **Field-level permissions**
  - Sensitive fields (e.g., internal notes) visible to admins only
  - Personal data masked for non-admin users

## 4. Export Pack Approach
- **Asynchronous Processing**
  1. User triggers export
  2. Backend creates ExportJob record
  3. Celery task processes in background
  4. Email notification with download link
  5. Files stored in S3 with 7-day expiration

## 5. Testing Plan
- **Unit Tests** (60% coverage)
  - Core business logic
  - Model methods
  - Utility functions

- **API Tests**
  - CRUD operations
  - Authentication/Authorization
  - Error handling

- **Integration Tests**
  - User workflows
  - Export functionality
  - Data consistency

- **Manual Testing**
  - UI/UX validation
  - Cross-browser testing
  - Mobile responsiveness

## 6. 8-Week Delivery Plan

### Milestone 1: Foundation (Weeks 1-2)
- Project setup
- Basic user authentication
- Core models and migrations
- Initial API endpoints

### Milestone 2: Core Features (Weeks 3-4)
- Request creation/management
- Task assignment workflow
- Basic audit logging
- Unit test coverage

### Milestone 3: Advanced Features (Weeks 5-6)
- Export functionality
- Advanced search/filtering
- Email notifications
- API documentation

### Milestone 4: Polish & Launch (Weeks 7-8)
- Performance optimization
- Security audit
- User acceptance testing
- Production deployment
- Documentation finalization
