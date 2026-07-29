const mongoose = require('mongoose');

const businessAnalysisSchema = new mongoose.Schema(
  {
    businessId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Business',
      required: true,
      index: true
    },
    strengths: {
      type: [String],
      default: []
    },
    weaknesses: {
      type: [String],
      default: []
    },
    opportunities: {
      type: [String],
      default: []
    },
    threats: {
      type: [String],
      default: []
    },
    growthRecommendations: {
      type: [mongoose.Schema.Types.Mixed],
      default: []
    }
  },
  { timestamps: { createdAt: true, updatedAt: false } }
);

module.exports = mongoose.model('BusinessAnalysis', businessAnalysisSchema, 'business_analyses');
