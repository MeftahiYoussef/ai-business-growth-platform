const express = require('express');
const { body } = require('express-validator');
const { listTrends, analyzeTrends } = require('../controllers/trends.controller');
const validate = require('../middleware/validate.middleware');

const router = express.Router();

router.get('/', listTrends);
router.post(
  '/analyze',
  [body('businessId').isMongoId().withMessage('businessId is required')],
  validate,
  analyzeTrends
);

module.exports = router;
