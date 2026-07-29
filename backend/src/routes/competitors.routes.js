const express = require('express');
const { body, param } = require('express-validator');
const {
  createCompetitor,
  listCompetitors,
  getCompetitor,
  updateCompetitor,
  deleteCompetitor,
  listCompetitorPosts,
  mockGenerateCompetitorPosts
} = require('../controllers/competitors.controller');
const validate = require('../middleware/validate.middleware');

const router = express.Router();

router.post(
  '/',
  [
    body('businessId').isMongoId().withMessage('businessId is required'),
    body('name').trim().notEmpty().withMessage('name is required'),
    body('platform').trim().notEmpty().withMessage('platform is required'),
    body('profileUrl').optional().trim(),
    body('followers').optional().isNumeric(),
    body('engagementRate').optional().isNumeric(),
    body('postingFrequency').optional().trim(),
    body('status').optional().isIn(['active', 'paused', 'archived'])
  ],
  validate,
  createCompetitor
);

router.get('/', listCompetitors);
router.get('/:id', [param('id').isMongoId()], validate, getCompetitor);
router.put('/:id', [param('id').isMongoId()], validate, updateCompetitor);
router.delete('/:id', [param('id').isMongoId()], validate, deleteCompetitor);
router.get('/:id/posts', [param('id').isMongoId()], validate, listCompetitorPosts);
router.post(
  '/:id/posts/mock-generate',
  [param('id').isMongoId(), body('count').optional().isInt({ min: 1, max: 25 })],
  validate,
  mockGenerateCompetitorPosts
);

module.exports = router;
