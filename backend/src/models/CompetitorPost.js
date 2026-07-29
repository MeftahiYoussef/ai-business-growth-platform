const mongoose = require('mongoose');

const competitorPostSchema = new mongoose.Schema(
  {
    competitorId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Competitor',
      required: true,
      index: true
    },
    businessId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Business',
      required: true,
      index: true
    },
    platform: {
      type: String,
      required: true,
      trim: true
    },
    postUrl: {
      type: String,
      trim: true
    },
    caption: {
      type: String,
      required: true
    },
    hashtags: {
      type: [String],
      default: []
    },
    hook: {
      type: String,
      required: true
    },
    format: {
      type: String,
      required: true
    },
    likes: {
      type: Number,
      default: 0
    },
    comments: {
      type: Number,
      default: 0
    },
    shares: {
      type: Number,
      default: 0
    },
    views: {
      type: Number,
      default: 0
    },
    engagementScore: {
      type: Number,
      default: 0
    },
    publishedAt: {
      type: Date,
      default: Date.now
    }
  },
  { timestamps: { createdAt: true, updatedAt: false } }
);

module.exports = mongoose.model('CompetitorPost', competitorPostSchema, 'competitor_posts');
