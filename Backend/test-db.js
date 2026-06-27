const { Client } = require('pg');

// Node.js automatically populates process.env from .env when run with --env-file
const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  console.error("Error: DATABASE_URL environment variable is not defined.");
  process.exit(1);
}

function parseConnectionString(str) {
  const withoutProtocol = str.replace(/^(postgresql\+asyncpg|postgresql|postgres):\/\//, '');
  const lastAtIndex = withoutProtocol.lastIndexOf('@');
  if (lastAtIndex === -1) {
    return { connectionString: str };
  }
  const credentials = withoutProtocol.substring(0, lastAtIndex);
  const hostPortDb = withoutProtocol.substring(lastAtIndex + 1);

  const colonIndex = credentials.indexOf(':');
  const user = colonIndex !== -1 ? credentials.substring(0, colonIndex) : credentials;
  const password = colonIndex !== -1 ? credentials.substring(colonIndex + 1) : '';

  const slashIndex = hostPortDb.indexOf('/');
  const hostPort = slashIndex !== -1 ? hostPortDb.substring(0, slashIndex) : hostPortDb;
  const database = slashIndex !== -1 ? hostPortDb.substring(slashIndex + 1) : '';

  const portColonIndex = hostPort.lastIndexOf(':');
  const host = portColonIndex !== -1 ? hostPort.substring(0, portColonIndex) : hostPort;
  const portStr = portColonIndex !== -1 ? hostPort.substring(portColonIndex + 1) : '5432';
  const port = parseInt(portStr, 10);

  return { user, password, host, port, database };
}

console.log("Attempting to connect to PostgreSQL database...");

const dbConfig = parseConnectionString(connectionString);
console.log("Parsed DB config:", { 
  host: dbConfig.host, 
  port: dbConfig.port, 
  user: dbConfig.user, 
  database: dbConfig.database,
  hasPassword: !!dbConfig.password
});
const client = new Client({
  ...dbConfig,
  ssl: {
    rejectUnauthorized: false // SSL is required by Supabase
  }
});

client.connect()
  .then(() => {
    console.log("✅ Successfully connected to the database!");
    return client.query("SELECT NOW(), version();");
  })
  .then(res => {
    console.log("Database current time:", res.rows[0].now);
    console.log("Database version:", res.rows[0].version);
    return client.end();
  })
  .catch(err => {
    console.error("❌ Connection failed!");
    console.error(err.message || err);
    process.exit(1);
  });
