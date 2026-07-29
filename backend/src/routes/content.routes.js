const express = require('express');
const { body, param } = require('express-validator');
const {
  listContentIdeas,
  generateIdeas,
  saveIdea,
  deleteIdea
} = require('../controllers/content.controller');
const validate = require('../middleware/validate.middleware');

const router = express.Router();

router.get('/', listContentIdeas);
router.post(
  '/generate',
  [
    body('businessId').isMongoId().withMessage('businessId is required'),
    body('count').optional().isInt({ min: 1, max: 25 })
  ],
  validate,
  generateIdeas
);
router.put('/:id/save', [param('id').isMongoId()], validate, saveIdea);
router.delete('/:id', [param('id').isMongoId()], validate, deleteIdea);

module.exports = router;
