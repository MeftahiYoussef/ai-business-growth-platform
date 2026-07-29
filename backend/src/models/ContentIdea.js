const mongoose = require('mongoose');

const contentIdeaSchema = new mongoose.Schema(
  {
    businessId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Business',
      required: true,
      index: true
    },
    title: {
      type: String,
      required: true,
      trim: true
    },
    hook: {
      type: String,
      required: true
    },
    caption: {
      type: String,
      required: true
    },
    cta: {
      type: String,
      required: true
    },
    hashtags: {
      type: [String],
      default: []
    },
    format: {
      type: String,
      required: true
    },
    engagementPotentialScore: {
      type: Number,
      required: true
    },
    trendMatchScore: {
      type: Number,
      required: true
    },
    reason: {
      type: String,
      default: ''
    },
    status: {
      type: String,
      enum: ['draft', 'saved', 'rejected'],
      default: 'draft'
    }
  },
  { timestamps: { createdAt: true, updatedAt: false } }
);

module.exports = mongoose.model('ContentIdea', contentIdeaSchema, 'content_ideas');
