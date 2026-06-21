# Example check: GET /users/{id}

Doc says path parameter `id` is required (good). Schema agrees.

Doc lists response fields `id, email, created_at`. Schema requires `id, email,
created_at, updated_at`. Finding: doc is missing `updated_at`.
