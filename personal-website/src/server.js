const express = require('express');
const session = require('express-session');
const path = require('path');
const { Pool } = require('pg');
const bcrypt = require('bcrypt');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const hpp = require('hpp');
const csurf = require('csurf');
const cookieParser = require('cookie-parser');

const app = express();
const port = process.env.PORT || 3000;

// Database connection
const pool = new Pool({
    user: process.env.POSTGRES_USER,
    host: process.env.POSTGRES_HOST,
    database: process.env.POSTGRES_DB,
    password: process.env.POSTGRES_PASSWORD,
    port: 5432,
});

// Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname, '../')));
app.use(session({
    secret: process.env.SESSION_SECRET || 'your-secret-key',
    resave: false,
    saveUninitialized: false
}));

// Security middleware
app.use(helmet());
app.use(cookieParser());

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100 // limit each IP to 100 requests per windowMs
});
app.use(limiter);

// Prevent HTTP Parameter Pollution
app.use(hpp());

// CSRF Protection
app.use(csurf({ cookie: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    sameSite: 'strict'
}}));

// Secure session configuration
app.use(session({
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
        secure: process.env.NODE_ENV === 'production',
        httpOnly: true,
        sameSite: 'strict',
        maxAge: 1000 * 60 * 60 // 1 hour
    },
    name: '_sid', // Change session cookie name
    store: new (require('connect-pg-simple')(session))({
        pool,
        tableName: 'session'
    })
}));

// Basic route for testing
app.get('/health', (req, res) => {
    res.json({ status: 'ok' });
});

// Initialize database
async function initializeDatabase() {
    try {
        console.log('Attempting database connection...');
        await pool.connect();
        console.log('Database connected successfully');

        console.log('Creating tables...');
        await pool.query(`
            CREATE TABLE IF NOT EXISTS visits (
                id SERIAL PRIMARY KEY,
                ip_address VARCHAR(45),
                user_agent TEXT,
                path VARCHAR(255),
                timestamp TIMESTAMP WITH TIME ZONE
            );

            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );
        `);
        console.log('Tables created successfully');

        return true;
    } catch (error) {
        console.error('Database initialization error:', error);
        return false;
    }
}

// Initialize admin user
async function initializeAdmin() {
    try {
        const adminUsername = process.env.ADMIN_USERNAME;
        const adminPassword = process.env.ADMIN_PASSWORD;

        if (!adminUsername || !adminPassword) {
            console.error('Admin credentials not provided in environment variables');
            return false;
        }

        console.log('Checking for existing admin...');
        const existingAdmin = await pool.query('SELECT * FROM admins WHERE username = $1', [adminUsername]);

        if (existingAdmin.rows.length === 0) {
            console.log('Creating new admin user...');
            const saltRounds = 10;
            const passwordHash = await bcrypt.hash(adminPassword, saltRounds);
            
            await pool.query(
                'INSERT INTO admins (username, password_hash) VALUES ($1, $2)',
                [adminUsername, passwordHash]
            );
            console.log('Admin user created successfully');
        } else {
            console.log('Admin user already exists');
        }

        return true;
    } catch (error) {
        console.error('Admin initialization error:', error);
        return false;
    }
}

// Visit tracking middleware
app.use(async (req, res, next) => {
    if (!req.path.startsWith('/static') && !req.path.startsWith('/admin')) {
        try {
            await pool.query(
                'INSERT INTO visits (ip_address, user_agent, path, timestamp) VALUES ($1, $2, $3, NOW())',
                [req.ip, req.headers['user-agent'], req.path]
            );
        } catch (error) {
            console.error('Error logging visit:', error);
        }
    }
    next();
});

// Admin routes
app.post('/admin/login', async (req, res) => {
    const { username, password } = req.body;
    console.log('Login attempt for:', username);

    try {
        const result = await pool.query('SELECT * FROM admins WHERE username = $1', [username]);
        const user = result.rows[0];

        if (!user) {
            console.log('User not found');
            return res.status(401).json({ success: false, message: 'Invalid credentials' });
        }

        const passwordMatch = await bcrypt.compare(password, user.password_hash);
        if (passwordMatch) {
            req.session.isAuthenticated = true;
            console.log('Login successful');
            return res.json({ success: true });
        } else {
            console.log('Invalid password');
            return res.status(401).json({ success: false, message: 'Invalid credentials' });
        }
    } catch (error) {
        console.error('Login error:', error);
        return res.status(500).json({ success: false, message: 'Server error' });
    }
});

app.use('/admin/dashboard', (req, res, next) => {
    if (req.session.isAuthenticated) {
        next();
    } else {
        res.redirect('/admin');
    }
});

app.get('/admin/dashboard', (req, res) => {
    res.sendFile(path.join(__dirname, '../admin/dashboard.html'));
});

// Add this function for database connection with retries
async function connectWithRetry(maxRetries = 5, delay = 5000) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            console.log(`Attempting database connection (attempt ${i + 1}/${maxRetries})...`);
            await pool.connect();
            console.log('Database connected successfully');
            return true;
        } catch (error) {
            console.error(`Connection attempt ${i + 1} failed:`, error.message);
            if (i < maxRetries - 1) {
                console.log(`Retrying in ${delay/1000} seconds...`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
    return false;
}

// Modify the startServer function
async function startServer() {
    try {
        // Wait for database connection
        const connected = await connectWithRetry();
        if (!connected) {
            throw new Error('Could not connect to database after multiple attempts');
        }

        const dbInitialized = await initializeDatabase();
        if (!dbInitialized) {
            throw new Error('Database initialization failed');
        }

        const adminInitialized = await initializeAdmin();
        if (!adminInitialized) {
            throw new Error('Admin initialization failed');
        }

        app.listen(port, () => {
            console.log(`Server running on port ${port}`);
        });
    } catch (error) {
        console.error('Server startup error:', error);
        process.exit(1);
    }
}

startServer(); 