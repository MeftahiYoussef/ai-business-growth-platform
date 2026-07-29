const express = require('express');
const { body } = require('express-validator');
const { getStrategy, generateBusinessStrategy } = require('../controllers/strategy.controller');
const validate = require('../middleware/validate.middleware');

const router = express.Router();

router.get('/', getStrategy);
router.post(
  '/generate',
  [body('businessId').isMongoId().withMessage('businessId is required')],
  validate,
  generateBusinessStrategy
);

module.exports = router;
