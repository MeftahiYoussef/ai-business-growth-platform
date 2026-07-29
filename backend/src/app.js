const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');

const protect = require('./middleware/auth.middleware');
const { notFound, errorHandler } = require('./middleware/error.middleware');

const authRoutes = require('./routes/auth.routes');
const businessRoutes = require('./routes/business.routes');
const competitorsRoutes = require('./routes/competitors.routes');
const trendsRoutes = require('./routes/trends.routes');
const contentRoutes = require('./routes/content.routes');
const strategyRoutes = require('./routes/strategy.routes');
const analysisRoutes = require('./routes/analysis.routes');
const feedbackRoutes = require('./routes/feedback.routes');

const app = express();

app.use(helmet());
app.use(cors({
  origin(origin, callback) {
    if (!origin || /^http:\/\/(localhost|127\.0\.0\.1):\d+$/.test(origin)) {
      return callback(null, true);
    }
    if (process.env.CLIENT_ORIGIN && origin === process.env.CLIENT_ORIGIN) {
      return callback(null, true);
    }
    return callback(null, false);
  },
  credentials: true,
  allowedHeaders: ['Content-Type', 'Authorization'],
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
}));
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true }));
app.use(morgan(process.env.NODE_ENV === 'production' ? 'combined' : 'dev'));

app.get('/health', (req, res) => {
  res.json({ success: true, status: 'ok' });
});

app.use('/api/auth', authRoutes);
app.use('/api/business', protect, businessRoutes);
app.use('/api/competitors', protect, competitorsRoutes);
app.use('/api/trends', protect, trendsRoutes);
app.use('/api/content-ideas', protect, contentRoutes);
app.use('/api/strategy', protect, strategyRoutes);
app.use('/api/analysis', protect, analysisRoutes);
app.use('/api/feedback', protect, feedbackRoutes);

app.use(notFound);
app.use(errorHandler);

module.exports = app;
