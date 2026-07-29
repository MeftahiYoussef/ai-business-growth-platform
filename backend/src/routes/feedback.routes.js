const express = require('express');
const { body } = require('express-validator');
const { createFeedback } = require('../controllers/feedback.controller');
const validate = require('../middleware/validate.middleware');

const router = express.Router();

router.post(
  '/',
  [
    body('businessId').isMongoId().withMessage('businessId is required'),
    body('contentIdeaId').isMongoId().withMessage('contentIdeaId is required'),
    body('liked').isBoolean().withMessage('liked must be true or false'),
    body('comment').optional().trim()
  ],
  validate,
  createFeedback
);

module.exports = router;
