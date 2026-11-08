-- =============================================================================
-- Local Farm and Market Food Availability System  (COSC444)
-- Sample (fictional) data. Dates are RELATIVE to the day this script is run, so the
-- demonstration data is always fresh (nothing is expired on demo day).
-- Demo accounts: admin1, farmer_ahmed, farmer_mariam, farmer_salem,
--                buyer_dubai, buyer_adcm, buyer_sharjah, buyer_alain   (password: Demo@1234)
-- =============================================================================
USE farm_market;

INSERT INTO units (unit_code, unit_name, category, to_base_factor) VALUES
('kg', 'Kilogram', 'mass', 1), ('g', 'Gram', 'mass', 0.001), ('tonne', 'Metric tonne', 'mass', 1000), ('crate', 'Crate', 'count', 1);
INSERT INTO crops (crop_name, category) VALUES
('Tomato', 'vegetable'), ('Cucumber', 'vegetable'), ('Bell Pepper', 'vegetable'), ('Lettuce', 'leafy'), ('Eggplant', 'vegetable'), ('Dates (Khalas)', 'fruit');
INSERT INTO farms (farm_name, emirate, location_desc, area_hectares) VALUES
('Al Ain Green Valley Farm', 'Abu Dhabi', 'Al Ain, Al Foah area', 12.5),
('Liwa Oasis Date Farm', 'Abu Dhabi', 'Liwa Oasis', 30.0),
('RAK Highland Farm', 'Ras Al Khaimah', 'Wadi Bih foothills', 8.0),
('Al Dhaid Sun Farm', 'Sharjah', 'Al Dhaid', 15.0);
INSERT INTO markets (market_name, emirate, address) VALUES
('Abu Dhabi Central Market', 'Abu Dhabi', 'Mina Zayed, Abu Dhabi'),
('Dubai Fresh Hub', 'Dubai', 'Al Aweer, Dubai'),
('Sharjah Souk Al Jubail', 'Sharjah', 'Al Jubail, Sharjah'),
('Al Ain Community Market', 'Abu Dhabi', 'Al Ain City');
INSERT INTO users (user_id, username, full_name, password_hash, role, market_id) VALUES
(1, 'admin1', 'Hessa Al Admin', '$2b$10$noenhZ0CFrlRpXW9tNhkjuPipMgB9fe22bnEsanDXq4s1.1AJnBCq', 'admin', NULL),
(2, 'farmer_ahmed', 'Ahmed Al Farmer', '$2b$10$qIc/R.Hthd3I1UI9uV.vne4x014xaGIfg/sF5rb41osfZredZP9Zu', 'farmer', NULL),
(3, 'farmer_mariam', 'Mariam Al Farmer', '$2b$10$9.KBfCfLvsvNUCbGxtaoZuJzWs296jVMx9/S50BAtlRJ6vNjyDDfm', 'farmer', NULL),
(4, 'farmer_salem', 'Salem Al Farmer', '$2b$10$avFzk1Q4rxOe8uCv61bEkuxvJUpk32eS0t6gkaTwRpXNFh/YMVUmW', 'farmer', NULL),
(5, 'buyer_adcm', 'Khalid (Abu Dhabi Central)', '$2b$10$I8N8dcNrVAgd6kpqUYXZluWkJwaTul8.xJ3PQFB96phcbShgw/U2q', 'buyer', 1),
(6, 'buyer_dubai', 'Noura (Dubai Fresh Hub)', '$2b$10$mI4iHsBi.Bs0KAzAwLOpT.Fq30FnijpI5gIpnUpzQ0HguKrYKloFC', 'buyer', 2),
(7, 'buyer_sharjah', 'Omar (Sharjah Souk)', '$2b$10$DFtewLTkupuRsrywwlJrbeSlMDSvFsV57fZgkkSSwEhp/PZSVWsii', 'buyer', 3),
(8, 'buyer_alain', 'Latifa (Al Ain Market)', '$2b$10$G2OzPipXb/YmMSjmyWZk5uh4XCDXEHylI4BnZU518w.iWe5LSkRWy', 'buyer', 4);
INSERT INTO user_farms (user_id, farm_id) VALUES (2, 1), (2, 2), (3, 3), (4, 4);
INSERT INTO crop_cycles (farm_id, crop_id, planting_date, expected_harvest_date, expected_quantity, expected_unit, status, notes) VALUES
(1, 1, DATE_SUB(CURDATE(), INTERVAL 95 DAY), DATE_SUB(CURDATE(), INTERVAL 12 DAY), 300, 'kg', 'HARVESTING', 'Sample cycle'),
(1, 2, DATE_SUB(CURDATE(), INTERVAL 70 DAY), DATE_SUB(CURDATE(), INTERVAL 8 DAY), 200, 'kg', 'HARVESTING', 'Sample cycle'),
(2, 6, DATE_SUB(CURDATE(), INTERVAL 400 DAY), DATE_SUB(CURDATE(), INTERVAL 5 DAY), 2, 'tonne', 'HARVESTING', 'Sample cycle'),
(3, 3, DATE_SUB(CURDATE(), INTERVAL 80 DAY), DATE_SUB(CURDATE(), INTERVAL 6 DAY), 250, 'kg', 'HARVESTING', 'Sample cycle'),
(3, 5, DATE_SUB(CURDATE(), INTERVAL 85 DAY), DATE_SUB(CURDATE(), INTERVAL 10 DAY), 180, 'kg', 'HARVESTING', 'Sample cycle'),
(4, 4, DATE_SUB(CURDATE(), INTERVAL 45 DAY), DATE_SUB(CURDATE(), INTERVAL 4 DAY), 150, 'kg', 'HARVESTING', 'Sample cycle'),
(4, 1, DATE_SUB(CURDATE(), INTERVAL 90 DAY), DATE_SUB(CURDATE(), INTERVAL 9 DAY), 260, 'kg', 'HARVESTING', 'Sample cycle'),
(1, 1, DATE_SUB(CURDATE(), INTERVAL 30 DAY), DATE_ADD(CURDATE(), INTERVAL 12 DAY), 320, 'kg', 'GROWING', 'Sample cycle'),
(3, 2, DATE_SUB(CURDATE(), INTERVAL 25 DAY), DATE_ADD(CURDATE(), INTERVAL 9 DAY), 220, 'kg', 'GROWING', 'Sample cycle');
INSERT INTO harvest_lots (cycle_id, crop_id, quantity, unit, harvest_date, sell_by_date) VALUES
(1, 1, 100, 'kg', DATE_SUB(CURDATE(), INTERVAL 12 DAY), DATE_ADD(CURDATE(), INTERVAL 3 DAY)),
(1, 1, 80, 'kg', DATE_SUB(CURDATE(), INTERVAL 9 DAY), DATE_ADD(CURDATE(), INTERVAL 6 DAY)),
(1, 1, 60, 'kg', DATE_SUB(CURDATE(), INTERVAL 3 DAY), DATE_ADD(CURDATE(), INTERVAL 10 DAY)),
(2, 2, 90, 'kg', DATE_SUB(CURDATE(), INTERVAL 8 DAY), DATE_ADD(CURDATE(), INTERVAL 4 DAY)),
(2, 2, 70, 'kg', DATE_SUB(CURDATE(), INTERVAL 2 DAY), DATE_ADD(CURDATE(), INTERVAL 9 DAY)),
(3, 6, 1.2, 'tonne', DATE_SUB(CURDATE(), INTERVAL 5 DAY), DATE_ADD(CURDATE(), INTERVAL 120 DAY)),
(4, 3, 110, 'kg', DATE_SUB(CURDATE(), INTERVAL 6 DAY), DATE_ADD(CURDATE(), INTERVAL 7 DAY)),
(4, 3, 85, 'kg', DATE_SUB(CURDATE(), INTERVAL 1 DAY), DATE_ADD(CURDATE(), INTERVAL 12 DAY)),
(5, 5, 95, 'kg', DATE_SUB(CURDATE(), INTERVAL 10 DAY), DATE_SUB(CURDATE(), INTERVAL 2 DAY)),
(5, 5, 70, 'kg', DATE_SUB(CURDATE(), INTERVAL 4 DAY), DATE_ADD(CURDATE(), INTERVAL 5 DAY)),
(6, 4, 60, 'kg', DATE_SUB(CURDATE(), INTERVAL 4 DAY), DATE_ADD(CURDATE(), INTERVAL 1 DAY)),
(6, 4, 55, 'kg', DATE_SUB(CURDATE(), INTERVAL 1 DAY), DATE_ADD(CURDATE(), INTERVAL 4 DAY)),
(7, 1, 120, 'kg', DATE_SUB(CURDATE(), INTERVAL 9 DAY), DATE_ADD(CURDATE(), INTERVAL 5 DAY)),
(7, 1, 90, 'kg', DATE_SUB(CURDATE(), INTERVAL 2 DAY), DATE_ADD(CURDATE(), INTERVAL 11 DAY));
INSERT INTO stock_movements (lot_id, movement_type, quantity, unit, movement_date, user_id, reason) VALUES
(1, 'HARVEST_ADDED', 100, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 12 DAY), '12:00:00'), 2, 'Harvest recorded'),
(2, 'HARVEST_ADDED', 80, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 9 DAY), '12:00:00'), 2, 'Harvest recorded'),
(3, 'HARVEST_ADDED', 60, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '12:00:00'), 2, 'Harvest recorded'),
(4, 'HARVEST_ADDED', 90, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 8 DAY), '12:00:00'), 2, 'Harvest recorded'),
(5, 'HARVEST_ADDED', 70, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '12:00:00'), 2, 'Harvest recorded'),
(6, 'HARVEST_ADDED', 1.2, 'tonne', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 5 DAY), '12:00:00'), 2, 'Harvest recorded'),
(7, 'HARVEST_ADDED', 110, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 6 DAY), '12:00:00'), 3, 'Harvest recorded'),
(8, 'HARVEST_ADDED', 85, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '12:00:00'), 3, 'Harvest recorded'),
(9, 'HARVEST_ADDED', 95, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 10 DAY), '12:00:00'), 3, 'Harvest recorded'),
(10, 'HARVEST_ADDED', 70, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '12:00:00'), 3, 'Harvest recorded'),
(11, 'HARVEST_ADDED', 60, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '12:00:00'), 4, 'Harvest recorded'),
(12, 'HARVEST_ADDED', 55, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '12:00:00'), 4, 'Harvest recorded'),
(13, 'HARVEST_ADDED', 120, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 9 DAY), '12:00:00'), 4, 'Harvest recorded'),
(14, 'HARVEST_ADDED', 90, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '12:00:00'), 4, 'Harvest recorded');
INSERT INTO market_requests (market_id, crop_id, quantity, unit, needed_by_date, status, notes, created_by, created_at, updated_at) VALUES
(2, 1, 150, 'kg', DATE_ADD(CURDATE(), INTERVAL 2 DAY), 'PARTIALLY_FULFILLED', 'Sample request', 6, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 10 DAY), '09:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 10 DAY), '09:00:00')),
(1, 2, 100, 'kg', DATE_ADD(CURDATE(), INTERVAL 3 DAY), 'PARTIALLY_FULFILLED', 'Sample request', 5, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 7 DAY), '09:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 7 DAY), '09:00:00')),
(3, 3, 120, 'kg', DATE_ADD(CURDATE(), INTERVAL 4 DAY), 'PARTIALLY_FULFILLED', 'Sample request', 7, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 6 DAY), '09:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 6 DAY), '09:00:00')),
(4, 6, 500, 'kg', DATE_ADD(CURDATE(), INTERVAL 5 DAY), 'FULFILLED', 'Sample request', 8, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 5 DAY), '09:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 5 DAY), '09:00:00')),
(2, 4, 80, 'kg', DATE_ADD(CURDATE(), INTERVAL 1 DAY), 'PARTIALLY_FULFILLED', 'Sample request', 6, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '09:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '09:00:00')),
(1, 1, 200, 'kg', DATE_ADD(CURDATE(), INTERVAL 6 DAY), 'PARTIALLY_ALLOCATED', 'Sample request', 5, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '09:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '09:00:00')),
(3, 5, 60, 'kg', DATE_ADD(CURDATE(), INTERVAL 3 DAY), 'FULFILLED', 'Sample request', 7, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '09:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '09:00:00')),
(4, 2, 50, 'kg', DATE_ADD(CURDATE(), INTERVAL 7 DAY), 'SUBMITTED', 'Sample request', 8, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '09:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '09:00:00'));
INSERT INTO request_status_history (request_id, old_status, new_status, changed_at, changed_by, reason) VALUES
(1, NULL, 'SUBMITTED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 10 DAY), '09:00:00'), 6, 'Request created'),
(2, NULL, 'SUBMITTED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 7 DAY), '09:00:00'), 5, 'Request created'),
(3, NULL, 'SUBMITTED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 6 DAY), '09:00:00'), 7, 'Request created'),
(4, NULL, 'SUBMITTED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 5 DAY), '09:00:00'), 8, 'Request created'),
(5, NULL, 'SUBMITTED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '09:00:00'), 6, 'Request created'),
(6, NULL, 'SUBMITTED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '09:00:00'), 5, 'Request created'),
(7, NULL, 'SUBMITTED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '09:00:00'), 7, 'Request created'),
(8, NULL, 'SUBMITTED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '09:00:00'), 8, 'Request created');
INSERT INTO allocations (allocation_id, request_id, lot_id, quantity, unit, status, allocated_by, allocated_at, closed_at) VALUES
(1, 1, 1, 100, 'kg', 'DELIVERED', 2, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 9 DAY), '10:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 7 DAY), '15:00:00')),
(2, 1, 2, 30, 'kg', 'DELIVERED', 2, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 7 DAY), '10:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 5 DAY), '15:00:00')),
(3, 2, 4, 60, 'kg', 'DELIVERED', 2, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 6 DAY), '10:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '15:00:00')),
(4, 2, 5, 40, 'kg', 'ACTIVE', 2, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '10:00:00'), NULL),
(5, 3, 7, 80, 'kg', 'DELIVERED', 3, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 5 DAY), '10:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '15:00:00')),
(6, 3, 8, 40, 'kg', 'DELIVERED', 3, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '10:00:00'), TIMESTAMP(CURDATE(), '15:00:00')),
(7, 4, 6, 0.5, 'tonne', 'DELIVERED', 2, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '10:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '15:00:00')),
(8, 5, 11, 50, 'kg', 'DELIVERED', 4, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '10:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '15:00:00')),
(9, 5, 12, 30, 'kg', 'ACTIVE', 4, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '10:00:00'), NULL),
(10, 6, 13, 100, 'kg', 'ACTIVE', 4, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '10:00:00'), NULL),
(11, 6, 14, 50, 'kg', 'ACTIVE', 4, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '10:00:00'), NULL),
(12, 7, 10, 60, 'kg', 'DELIVERED', 3, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '10:00:00'), TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '15:00:00'));
INSERT INTO stock_movements (lot_id, movement_type, quantity, unit, movement_date, user_id, reason, allocation_id) VALUES
(1, 'RESERVED', 100, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 9 DAY), '10:00:00'), 2, 'Allocated to request #1', 1),
(1, 'DELIVERY', 95, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 7 DAY), '15:00:00'), 6, 'Delivered to request #1', 1),
(1, 'RESERVATION_RELEASED', 5, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 7 DAY), '15:00:00'), 6, 'Delivery shortfall: 5 kg damaged in transit', 1),
(2, 'RESERVED', 30, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 7 DAY), '10:00:00'), 2, 'Allocated to request #1', 2),
(2, 'DELIVERY', 30, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 5 DAY), '15:00:00'), 6, 'Delivered to request #1', 2),
(4, 'RESERVED', 60, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 6 DAY), '10:00:00'), 2, 'Allocated to request #2', 3),
(4, 'DELIVERY', 60, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '15:00:00'), 5, 'Delivered to request #2', 3),
(5, 'RESERVED', 40, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '10:00:00'), 2, 'Allocated to request #2', 4),
(7, 'RESERVED', 80, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 5 DAY), '10:00:00'), 3, 'Allocated to request #3', 5),
(7, 'DELIVERY', 78, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '15:00:00'), 7, 'Delivered to request #3', 5),
(7, 'RESERVATION_RELEASED', 2, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '15:00:00'), 7, 'Delivery shortfall: 2 kg under-weight on arrival', 5),
(8, 'RESERVED', 40, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '10:00:00'), 3, 'Allocated to request #3', 6),
(8, 'DELIVERY', 40, 'kg', TIMESTAMP(CURDATE(), '15:00:00'), 7, 'Delivered to request #3', 6),
(6, 'RESERVED', 0.5, 'tonne', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '10:00:00'), 2, 'Allocated to request #4', 7),
(6, 'DELIVERY', 0.5, 'tonne', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '15:00:00'), 8, 'Delivered to request #4', 7),
(11, 'RESERVED', 50, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '10:00:00'), 4, 'Allocated to request #5', 8),
(11, 'DELIVERY', 48, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '15:00:00'), 6, 'Delivered to request #5', 8),
(11, 'RESERVATION_RELEASED', 2, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '15:00:00'), 6, 'Delivery shortfall: 2 kg wilted on arrival', 8),
(12, 'RESERVED', 30, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '10:00:00'), 4, 'Allocated to request #5', 9),
(13, 'RESERVED', 100, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '10:00:00'), 4, 'Allocated to request #6', 10),
(14, 'RESERVED', 50, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '10:00:00'), 4, 'Allocated to request #6', 11),
(10, 'RESERVED', 60, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '10:00:00'), 3, 'Allocated to request #7', 12),
(10, 'DELIVERY', 60, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '15:00:00'), 7, 'Delivered to request #7', 12);
INSERT INTO delivery_receipts (allocation_id, allocated_quantity, received_quantity, discrepancy, discrepancy_reason, received_date, received_by, created_at) VALUES
(1, 100, 95, -5, '5 kg damaged in transit', DATE_SUB(CURDATE(), INTERVAL 7 DAY), 6, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 7 DAY), '15:00:00')),
(2, 30, 30, 0, NULL, DATE_SUB(CURDATE(), INTERVAL 5 DAY), 6, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 5 DAY), '15:00:00')),
(3, 60, 60, 0, NULL, DATE_SUB(CURDATE(), INTERVAL 4 DAY), 5, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '15:00:00')),
(5, 80, 78, -2, '2 kg under-weight on arrival', DATE_SUB(CURDATE(), INTERVAL 3 DAY), 7, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '15:00:00')),
(6, 40, 40, 0, NULL, CURDATE(), 7, TIMESTAMP(CURDATE(), '15:00:00')),
(7, 0.5, 0.5, 0.0, NULL, DATE_SUB(CURDATE(), INTERVAL 2 DAY), 8, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '15:00:00')),
(8, 50, 48, -2, '2 kg wilted on arrival', DATE_SUB(CURDATE(), INTERVAL 1 DAY), 6, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '15:00:00')),
(12, 60, 60, 0, NULL, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 7, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '15:00:00'));
INSERT INTO stock_movements (lot_id, movement_type, quantity, unit, movement_date, user_id, reason) VALUES
(9, 'LOSS', 95, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '08:00:00'), 3, 'Expired before sale - spoilage'),
(11, 'LOSS', 5, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '08:00:00'), 4, 'Wilting damage'),
(3, 'LOSS', 4, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '09:00:00'), 2, 'Bruising during handling'),
(14, 'CORRECTION_ADD', 2, 'kg', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '11:00:00'), 1, 'Approved correction: scale recalibration found under-count');
INSERT INTO request_status_history (request_id, old_status, new_status, changed_at, changed_by, reason) VALUES
(1, 'SUBMITTED', 'PARTIALLY_ALLOCATED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 9 DAY), '15:00:00'), 2, 'Allocation created'),
(1, 'PARTIALLY_ALLOCATED', 'PARTIALLY_FULFILLED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 7 DAY), '15:00:00'), 6, 'Delivery confirmed'),
(2, 'SUBMITTED', 'PARTIALLY_ALLOCATED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 6 DAY), '15:00:00'), 2, 'Allocation created'),
(2, 'PARTIALLY_ALLOCATED', 'PARTIALLY_FULFILLED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '15:00:00'), 5, 'Delivery confirmed'),
(3, 'SUBMITTED', 'PARTIALLY_ALLOCATED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 5 DAY), '15:00:00'), 3, 'Allocation created'),
(3, 'PARTIALLY_ALLOCATED', 'PARTIALLY_FULFILLED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '15:00:00'), 7, 'Delivery confirmed'),
(4, 'SUBMITTED', 'ALLOCATED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '15:00:00'), 2, 'Allocation created'),
(4, 'ALLOCATED', 'FULFILLED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '15:00:00'), 8, 'Delivery confirmed'),
(5, 'SUBMITTED', 'PARTIALLY_ALLOCATED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '15:00:00'), 4, 'Allocation created'),
(5, 'PARTIALLY_ALLOCATED', 'PARTIALLY_FULFILLED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '15:00:00'), 6, 'Delivery confirmed'),
(6, 'SUBMITTED', 'PARTIALLY_ALLOCATED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '15:00:00'), 4, 'Allocation created'),
(7, 'SUBMITTED', 'PARTIALLY_ALLOCATED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '15:00:00'), 3, 'Allocation created'),
(7, 'PARTIALLY_ALLOCATED', 'FULFILLED', TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '15:00:00'), 7, 'Delivery confirmed');
INSERT INTO harvest_lot_images (lot_id, file_path, mime_type, caption, uploaded_by, uploaded_at) VALUES
(1, 'images/lots/lot_01.jpg', 'image/jpeg', 'Tomato lot #1 (sample)', 2, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 12 DAY), '13:00:00')),
(2, 'images/lots/lot_02.jpg', 'image/jpeg', 'Tomato lot #2 (sample)', 2, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 9 DAY), '13:00:00')),
(3, 'images/lots/lot_03.jpg', 'image/jpeg', 'Tomato lot #3 (sample)', 2, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 3 DAY), '13:00:00')),
(4, 'images/lots/lot_04.jpg', 'image/jpeg', 'Cucumber lot #4 (sample)', 2, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 8 DAY), '13:00:00')),
(5, 'images/lots/lot_05.jpg', 'image/jpeg', 'Cucumber lot #5 (sample)', 2, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 2 DAY), '13:00:00')),
(6, 'images/lots/lot_06.jpg', 'image/jpeg', 'Dates (Khalas) lot #6 (sample)', 2, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 5 DAY), '13:00:00')),
(7, 'images/lots/lot_07.jpg', 'image/jpeg', 'Bell Pepper lot #7 (sample)', 3, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 6 DAY), '13:00:00')),
(8, 'images/lots/lot_08.jpg', 'image/jpeg', 'Bell Pepper lot #8 (sample)', 3, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '13:00:00')),
(9, 'images/lots/lot_09.jpg', 'image/jpeg', 'Eggplant lot #9 (sample)', 3, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 10 DAY), '13:00:00')),
(10, 'images/lots/lot_10.jpg', 'image/jpeg', 'Eggplant lot #10 (sample)', 3, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '13:00:00')),
(11, 'images/lots/lot_11.jpg', 'image/jpeg', 'Lettuce lot #11 (sample)', 4, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 4 DAY), '13:00:00')),
(12, 'images/lots/lot_12.jpg', 'image/jpeg', 'Lettuce lot #12 (sample)', 4, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '13:00:00')),
(12, 'images/lots/missing_lot_12.jpg', 'image/jpeg', 'Photo file missing (demo of graceful handling)', 4, TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '13:30:00'));
