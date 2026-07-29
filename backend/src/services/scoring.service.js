const calculateEngagementScore = ({ likes = 0, comments = 0, shares = 0, views = 0 }) => {
  if (!views) {
    return Math.min(100, likes * 0.2 + comments * 1.5 + shares * 2);
  }

  const weighted = likes + comments * 4 + shares * 6;
  return Math.min(100, Math.round((weighted / views) * 1000));
};

const calculateTrendScore = ({ growthRate = 0, confidence = 0.75, sourceCount = 1 }) => {
  return Math.min(100, Math.round(growthRate * 0.45 + confidence * 35 + sourceCount * 8));
};

const getPagination = (query) => {
  const page = Math.max(parseInt(query.page, 10) || 1, 1);
  const limit = Math.min(Math.max(parseInt(query.limit, 10) || 10, 1), 100);
  const skip = (page - 1) * limit;
  const sortBy = query.sortBy || 'createdAt';
  const sortOrder = query.sortOrder === 'asc' ? 1 : -1;

  return { page, limit, skip, sort: { [sortBy]: sortOrder } };
};

const paginatedResponse = async (model, filter, query, searchFields = []) => {
  const { page, limit, skip, sort } = getPagination(query);
  const search = query.search?.trim();
  const finalFilter = { ...filter };

  if (search && searchFields.length) {
    finalFilter.$or = searchFields.map((field) => ({
      [field]: { $regex: search, $options: 'i' }
    }));
  }

  const [items, total] = await Promise.all([
    model.find(finalFilter).sort(sort).skip(skip).limit(limit),
    model.countDocuments(finalFilter)
  ]);

  return {
    items,
    pagination: {
      page,
      limit,
      total,
      pages: Math.ceil(total / limit)
    }
  };
};

module.exports = {
  calculateEngagementScore,
  calculateTrendScore,
  paginatedResponse
};
