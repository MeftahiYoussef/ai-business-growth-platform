const mongoose = require('mongoose');

const competitorSchema = new mongoose.Schema(
  {
    businessId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Business',
      required: true,
      index: true
    },
    name: {
      type: String,
      required: true,
      trim: true
    },
    platform: {
      type: String,
      required: true,
      trim: true
    },
    profileUrl: {
      type: String,
      trim: true
    },
    followers: {
      type: Number,
      default: 0
    },
    engagementRate: {
      type: Number,
      default: 0
    },
    postingFrequency: {
      type: String,
      default: 'Unknown'
    },
    status: {
      type: String,
      enum: ['active', 'paused', 'archived'],
      default: 'active'
    }
  },
  { timestamps: true }
);

module.exports = mongoose.model('Competitor', competitorSchema);
