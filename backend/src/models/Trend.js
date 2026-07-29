const mongoose = require('mongoose');

const trendSchema = new mongoose.Schema(
  {
    businessId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Business',
      required: true,
      index: true
    },
    topic: {
      type: String,
      required: true,
      trim: true
    },
    hashtags: {
      type: [String],
      default: []
    },
    hooks: {
      type: [String],
      default: []
    },
    format: {
      type: String,
      required: true
    },
    momentumLabel: {
      type: String,
      enum: ['Emerging', 'Peaking', 'Fading'],
      required: true
    },
    trendScore: {
      type: Number,
      required: true
    },
    growthRate: {
      type: Number,
      default: 0
    },
    confidence: {
      type: Number,
      default: 0.75
    },
    explanation: {
      type: String,
      default: ''
    },
    sourcePosts: [
      {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'CompetitorPost'
      }
    ]
  },
  { timestamps: { createdAt: true, updatedAt: false } }
);

module.exports = mongoose.model('Trend', trendSchema);
