# Project Management API

A backend API service for managing projects and data sources, backed by AWS DocumentDB/MongoDB.

## Features

- Project management with CRUD operations
- Data source management with various types (GitHub, Google Docs, Databricks, etc.)
- Connection validation for data sources
- RESTful API design

## Requirements

- Python 3.12+
- MongoDB/DocumentDB
- Docker (optional, for containerization)

## Installation

1. Clone the repository

```bash
git clone <repository-url>
cd backend
```

2. Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up MongoDB

You can run MongoDB locally using Docker:

```bash
docker run -d --name mongodb -p 27017:27017 mongo
```

4. Set up environment variables

Create a `.env` file in the root directory with the following variables:

```
MONGODB_URI=mongodb://localhost:27017/chicory?retryWrites=false
```

If you're using MongoDB with authentication or a remote instance, adjust the URI accordingly:

```
MONGODB_URI=mongodb://<username>:<password>@<host>:<port>/<database>?retryWrites=false
```

## Running the Application

### Development

```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

### Production

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Using Docker

#### Building and Running Individual Containers

1. **Build the Docker image**

```bash
# Navigate to the project directory
cd backend

# Build the image with a tag
docker build -t chicory-backend .
```

2. **View the built images**

```bash
docker images
```

You should see your image listed as `chicory-backend`

3. **Run the container**

```bash
docker run -d --name chicory-api -p 8000:8000 --env-file .env chicory-backend
```

4. **Check running containers**

```bash
docker ps
```

5. **View container logs**

```bash
docker logs chicory-api
```

#### Setting up MongoDB with Docker Network

1. **Create a Docker network**

```bash
docker network create chicory-network
```

2. **Run MongoDB in the network**

```bash
docker run -d --name mongodb \
  --network chicory-network \
  -p 27017:27017 \
  -v mongo_data:/data/db \
  mongo
```

3. **Run the API in the same network**

```bash
docker run -d --name chicory-api \
  --network chicory-network \
  -p 8000:8000 \
  --env-file .env \
  chicory-backend
```

4. **Verify network connection**

```bash
# List networks
docker network ls

# Inspect network
docker network inspect chicory-network
```

When using the shared network, update your `.env` file to use the container name as the host:

```
MONGODB_URI=mongodb://mongodb:27017/chicory?retryWrites=false
```

#### Managing Docker Containers

1. **Stop containers**

```bash
docker stop chicory-api mongodb
```

2. **Remove containers**

```bash
docker rm chicory-api mongodb
```

3. **Remove images**

```bash
docker rmi chicory-backend mongo
```

4. **Remove volumes**

```bash
docker volume rm mongo_data
```

## API Documentation

Once the application is running, you can access the auto-generated API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Projects

- `POST /projects` - Create a new project (requires organization_id)
- `GET /projects/{project_id}` - Get a project by ID
- `PUT /projects/{project_id}` - Update a project (requires organization_id)
- `GET /projects` - List all projects (requires organization_id)
- `DELETE /projects/{project_id}` - Delete a project (requires organization_id)

### Data Sources

- `GET /data-source-types` - List all available data source types
- `POST /projects/{project_id}/data-sources` - Connect a data source to a project (requires project_id)
- `POST /projects/{project_id}/data-sources/{data_source_id}/validate` - Test the connection to a data source (requires project_id and data_source_id)
- `GET /projects/{project_id}/data-sources` - List all data sources connected to a project (requires project_id)
- `PUT /projects/{project_id}/data-sources/{data_source_id}` - Update an existing data source (requires project_id and data_source_id)
- `DELETE /projects/{project_id}/data-sources/{data_source_id}` - Delete a data source (requires project_id and data_source_id)

## Testing

Run the tests with pytest:

```bash
pytest
```
