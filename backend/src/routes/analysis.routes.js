const express = require('express');
const { body } = require('express-validator');
const { getAnalysis, generateAnalysis } = require('../controllers/analysis.controller');
const validate = require('../middleware/validate.middleware');

const router = express.Router();

router.get('/', getAnalysis);
router.post(
  '/generate',
  [body('businessId').isMongoId().withMessage('businessId is required')],
  validate,
  generateAnalysis
);

module.exports = router;
