const ApiError = require('../utils/ApiError');

const notFound = (req, res, next) => {
  next(new ApiError(404, `Route not found: ${req.originalUrl}`));
};

const errorHandler = (err, req, res, next) => {
  let statusCode = err.statusCode || 500;
  let message = err.message || 'Internal server error';
  let details = err.details || undefined;

  if (err.name === 'ValidationError') {
    statusCode = 422;
    message = 'Validation failed';
    details = Object.values(err.errors).map((item) => ({
      field: item.path,
      message: item.message
    }));
  }

  if (err.name === 'CastError') {
    statusCode = 400;
    message = `Invalid ${err.path}`;
  }

  if (err.code === 11000) {
    statusCode = 409;
    message = 'Duplicate resource';
    details = err.keyValue;
  }

  res.status(statusCode).json({
    success: false,
    message,
    details,
    stack: process.env.NODE_ENV === 'production' ? undefined : err.stack
  });
};

module.exports = { notFound, errorHandler };
