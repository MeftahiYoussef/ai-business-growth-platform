const express = require('express');
const { body, param } = require('express-validator');
const {
  createBusiness,
  getMyBusiness,
  updateBusiness
} = require('../controllers/business.controller');
const validate = require('../middleware/validate.middleware');

const router = express.Router();

const createBusinessFields = () => [
  body('name').trim().notEmpty().withMessage('name is required'),
  body('industry').trim().notEmpty().withMessage('industry is required'),
  body('country').trim().notEmpty().withMessage('country is required'),
  body('productOrService').trim().notEmpty().withMessage('productOrService is required'),
  body('targetAudience').trim().notEmpty().withMessage('targetAudience is required'),
  body('goals').optional().isArray(),
  body('knownCompetitors').optional().isArray(),
  body('brandVoice').optional().trim()
];

const updateBusinessFields = () => [
  param('id').isMongoId(),
  body('name').optional().trim().notEmpty(),
  body('industry').optional().trim().notEmpty(),
  body('country').optional().trim().notEmpty(),
  body('productOrService').optional().trim().notEmpty(),
  body('targetAudience').optional().trim().notEmpty(),
  body('goals').optional().isArray(),
  body('knownCompetitors').optional().isArray(),
  body('brandVoice').optional().trim()
];

router.post('/', createBusinessFields(), validate, createBusiness);
router.get('/me', getMyBusiness);
router.put('/:id', updateBusinessFields(), validate, updateBusiness);

module.exports = router;
