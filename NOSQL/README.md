# Token Analyzer Project

## Overview
The Token Analyzer project is designed to provide a robust environment for analyzing tokens using MongoDB and Redis. This project utilizes Docker Compose for easy deployment and management of services.

## Project Structure
```
token-analyzer
├── docker-compose.yml       # Defines the services for MongoDB and Redis
├── mongo-init.js           # Optional MongoDB initialization script
├── .env                     # Environment variables for configuration
├── .gitignore               # Files and directories to ignore in Git
├── README.md                # Project documentation
├── docker
│   └── redis.conf          # Configuration settings for Redis server
└── scripts
    └── verify_connections.sh # Script to verify connections to MongoDB and Redis
```

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd token-analyzer
   ```

2. **Create a `.env` File**
   Create a `.env` file in the project root to store environment variables. Example:
   ```
   MONGO_INITDB_ROOT_PASSWORD=yourpassword
   REDIS_PASSWORD=yourpassword
   ```

3. **Start the Services**
   Use Docker Compose to start the MongoDB and Redis services:
   ```bash
   docker-compose up -d
   ```

4. **Verify Connections**
   After the services are up, you can run the verification script to ensure both databases are accessible:
   ```bash
   ./scripts/verify_connections.sh
   ```

## Usage
- Connect to MongoDB using the credentials defined in the `.env` file.
- Connect to Redis using the password specified in the `.env` file.

## Additional Information
- The `mongo-init.js` script is optional and can be modified to include additional initialization logic.
- The `redis.conf` file can be customized to change Redis server settings as needed.

## License
This project is licensed under the MIT License.