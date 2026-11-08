-- =============================================================================
-- Local Farm and Market Food Availability System  (COSC444)
-- MySQL 8.0 schema: tables, constraints, triggers and views
-- Safe to re-run: it drops and recreates every object in the farm_market database.
-- =============================================================================
CREATE DATABASE IF NOT EXISTS farm_market CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE farm_market;

SET FOREIGN_KEY_CHECKS = 0;
DROP VIEW  IF EXISTS v_users, v_cycles, v_receipts, v_movements, v_allocations,
                     v_request_summary, v_lot_details, v_lot_stock;
DROP TABLE IF EXISTS audit_log, delivery_receipts, stock_movements, allocations,
                     request_status_history, market_requests, harvest_lot_images,
                     harvest_lots, crop_cycles, user_farms, users, markets, farms,
                     crops, units;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------- reference data
CREATE TABLE units (
  unit_code      VARCHAR(20)   NOT NULL PRIMARY KEY,
  unit_name      VARCHAR(60)   NOT NULL,
  category       VARCHAR(10)   NOT NULL,
  to_base_factor DECIMAL(18,6) NOT NULL COMMENT 'multiply by this to get the base unit (kg for mass)',
  is_active      TINYINT(1)    NOT NULL DEFAULT 1,
  CONSTRAINT ck_units_category CHECK (category IN ('mass','count')),
  CONSTRAINT ck_units_factor   CHECK (to_base_factor > 0)
) ENGINE=InnoDB;

CREATE TABLE crops (
  crop_id    INT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
  crop_name  VARCHAR(60) NOT NULL,
  category   VARCHAR(20) NOT NULL,
  is_active  TINYINT(1)  NOT NULL DEFAULT 1,
  CONSTRAINT uq_crops_name UNIQUE (crop_name),
  CONSTRAINT ck_crops_category CHECK (category IN ('vegetable','fruit','leafy','herb'))
) ENGINE=InnoDB;

CREATE TABLE farms (
  farm_id        INT           NOT NULL AUTO_INCREMENT PRIMARY KEY,
  farm_name      VARCHAR(100)  NOT NULL,
  emirate        VARCHAR(30)   NOT NULL,
  location_desc  VARCHAR(200)  NULL,
  area_hectares  DECIMAL(10,3) NULL,
  is_active      TINYINT(1)    NOT NULL DEFAULT 1,
  CONSTRAINT uq_farms_name UNIQUE (farm_name),
  CONSTRAINT ck_farms_emirate CHECK (emirate IN ('Abu Dhabi','Dubai','Sharjah','Ajman','Umm Al Quwain','Ras Al Khaimah','Fujairah')),
  CONSTRAINT ck_farms_area CHECK (area_hectares IS NULL OR area_hectares > 0)
) ENGINE=InnoDB;

CREATE TABLE markets (
  market_id    INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
  market_name  VARCHAR(100) NOT NULL,
  emirate      VARCHAR(30)  NOT NULL,
  address      VARCHAR(200) NULL,
  is_active    TINYINT(1)   NOT NULL DEFAULT 1,
  CONSTRAINT uq_markets_name UNIQUE (market_name),
  CONSTRAINT ck_markets_emirate CHECK (emirate IN ('Abu Dhabi','Dubai','Sharjah','Ajman','Umm Al Quwain','Ras Al Khaimah','Fujairah'))
) ENGINE=InnoDB;

-- ---------------------------------------------------------------- users & access
CREATE TABLE users (
  user_id         INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username        VARCHAR(50)  NOT NULL,
  full_name       VARCHAR(100) NOT NULL,
  password_hash   VARCHAR(100) NOT NULL COMMENT 'bcrypt hash, never the plain password',
  role            VARCHAR(10)  NOT NULL,
  market_id       INT          NULL,
  is_active       TINYINT(1)   NOT NULL DEFAULT 1,
  failed_attempts INT          NOT NULL DEFAULT 0,
  locked_until    DATETIME     NULL,
  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_users_username UNIQUE (username),
  CONSTRAINT ck_users_role CHECK (role IN ('farmer','buyer','admin')),
  CONSTRAINT ck_users_failed CHECK (failed_attempts >= 0),
  CONSTRAINT ck_users_market_role CHECK ((role = 'buyer' AND market_id IS NOT NULL) OR (role <> 'buyer' AND market_id IS NULL)),
  CONSTRAINT fk_users_market FOREIGN KEY (market_id) REFERENCES markets(market_id)
) ENGINE=InnoDB;

CREATE TABLE user_farms (
  user_id INT NOT NULL,
  farm_id INT NOT NULL,
  PRIMARY KEY (user_id, farm_id),
  CONSTRAINT fk_uf_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  CONSTRAINT fk_uf_farm FOREIGN KEY (farm_id) REFERENCES farms(farm_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------- production
CREATE TABLE crop_cycles (
  cycle_id              INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  farm_id               INT NOT NULL,
  crop_id               INT NOT NULL,
  planting_date         DATE NOT NULL,
  expected_harvest_date DATE NOT NULL COMMENT 'FORECAST - never counted as stock',
  expected_quantity     DECIMAL(12,3) NOT NULL COMMENT 'FORECAST - never counted as stock',
  expected_unit         VARCHAR(20) NOT NULL,
  status                VARCHAR(12) NOT NULL DEFAULT 'GROWING',
  notes                 VARCHAR(200) NULL,
  is_active             TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT uq_cycle UNIQUE (farm_id, crop_id, planting_date),
  CONSTRAINT ck_cycle_qty CHECK (expected_quantity >= 0),
  CONSTRAINT ck_cycle_dates CHECK (expected_harvest_date >= planting_date),
  CONSTRAINT ck_cycle_status CHECK (status IN ('PLANNED','GROWING','HARVESTING','COMPLETED','CANCELLED')),
  CONSTRAINT fk_cycle_farm FOREIGN KEY (farm_id) REFERENCES farms(farm_id),
  CONSTRAINT fk_cycle_crop FOREIGN KEY (crop_id) REFERENCES crops(crop_id),
  CONSTRAINT fk_cycle_unit FOREIGN KEY (expected_unit) REFERENCES units(unit_code)
) ENGINE=InnoDB;

CREATE TABLE harvest_lots (
  lot_id       INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  cycle_id     INT NOT NULL,
  crop_id      INT NOT NULL,
  quantity     DECIMAL(12,3) NOT NULL COMMENT 'quantity harvested into this lot',
  unit         VARCHAR(20) NOT NULL,
  harvest_date DATE NOT NULL,
  sell_by_date DATE NULL,
  is_active    TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT ck_lot_qty CHECK (quantity > 0),
  CONSTRAINT ck_lot_sellby CHECK (sell_by_date IS NULL OR sell_by_date >= harvest_date),
  CONSTRAINT fk_lot_cycle FOREIGN KEY (cycle_id) REFERENCES crop_cycles(cycle_id),
  CONSTRAINT fk_lot_crop  FOREIGN KEY (crop_id)  REFERENCES crops(crop_id),
  CONSTRAINT fk_lot_unit  FOREIGN KEY (unit)     REFERENCES units(unit_code),
  INDEX idx_lots_cycle (cycle_id)
) ENGINE=InnoDB;

CREATE TABLE harvest_lot_images (
  image_id    INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  lot_id      INT NOT NULL,
  file_path   VARCHAR(255) NOT NULL COMMENT 'path relative to the project folder',
  mime_type   VARCHAR(20)  NOT NULL,
  caption     VARCHAR(200) NULL,
  uploaded_by INT NOT NULL,
  uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_active   TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT uq_image_path UNIQUE (file_path),
  CONSTRAINT ck_image_mime CHECK (mime_type IN ('image/jpeg','image/png')),
  CONSTRAINT fk_img_lot  FOREIGN KEY (lot_id) REFERENCES harvest_lots(lot_id),
  CONSTRAINT fk_img_user FOREIGN KEY (uploaded_by) REFERENCES users(user_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------- demand & allocation
CREATE TABLE market_requests (
  request_id     INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  market_id      INT NOT NULL,
  crop_id        INT NOT NULL,
  quantity       DECIMAL(12,3) NOT NULL,
  unit           VARCHAR(20) NOT NULL,
  needed_by_date DATE NOT NULL,
  status         VARCHAR(20) NOT NULL DEFAULT 'SUBMITTED',
  notes          VARCHAR(200) NULL,
  created_by     INT NOT NULL,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT ck_req_qty CHECK (quantity > 0),
  CONSTRAINT ck_req_status CHECK (status IN ('SUBMITTED','PARTIALLY_ALLOCATED','ALLOCATED','PARTIALLY_FULFILLED','FULFILLED','CLOSED','CANCELLED')),
  CONSTRAINT fk_req_market FOREIGN KEY (market_id) REFERENCES markets(market_id),
  CONSTRAINT fk_req_crop   FOREIGN KEY (crop_id)   REFERENCES crops(crop_id),
  CONSTRAINT fk_req_unit   FOREIGN KEY (unit)      REFERENCES units(unit_code),
  CONSTRAINT fk_req_user   FOREIGN KEY (created_by) REFERENCES users(user_id),
  INDEX idx_req_market (market_id)
) ENGINE=InnoDB;

CREATE TABLE request_status_history (
  history_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  request_id INT NOT NULL,
  old_status VARCHAR(20) NULL,
  new_status VARCHAR(20) NOT NULL,
  changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  changed_by INT NOT NULL,
  reason     VARCHAR(255) NULL,
  CONSTRAINT fk_hist_req  FOREIGN KEY (request_id) REFERENCES market_requests(request_id),
  CONSTRAINT fk_hist_user FOREIGN KEY (changed_by) REFERENCES users(user_id)
) ENGINE=InnoDB;

CREATE TABLE allocations (
  allocation_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  request_id    INT NOT NULL,
  lot_id        INT NOT NULL,
  quantity      DECIMAL(12,3) NOT NULL,
  unit          VARCHAR(20) NOT NULL,
  status        VARCHAR(10) NOT NULL DEFAULT 'ACTIVE',
  allocated_by  INT NOT NULL,
  allocated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  closed_at     DATETIME NULL,
  CONSTRAINT ck_alloc_qty CHECK (quantity > 0),
  CONSTRAINT ck_alloc_status CHECK (status IN ('ACTIVE','DELIVERED','RELEASED')),
  CONSTRAINT fk_alloc_req  FOREIGN KEY (request_id) REFERENCES market_requests(request_id),
  CONSTRAINT fk_alloc_lot  FOREIGN KEY (lot_id)     REFERENCES harvest_lots(lot_id),
  CONSTRAINT fk_alloc_unit FOREIGN KEY (unit)       REFERENCES units(unit_code),
  CONSTRAINT fk_alloc_user FOREIGN KEY (allocated_by) REFERENCES users(user_id),
  INDEX idx_alloc_request (request_id),
  INDEX idx_alloc_lot (lot_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------- stock ledger
-- Stock is NEVER stored as a number: it is always derived from these dated movements.
CREATE TABLE stock_movements (
  movement_id   INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  lot_id        INT NOT NULL,
  movement_type VARCHAR(25) NOT NULL,
  quantity      DECIMAL(12,3) NOT NULL,
  unit          VARCHAR(20) NOT NULL,
  movement_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_id       INT NOT NULL,
  reason        VARCHAR(255) NULL,
  allocation_id INT NULL,
  CONSTRAINT ck_move_qty CHECK (quantity > 0),
  CONSTRAINT ck_move_type CHECK (movement_type IN ('HARVEST_ADDED','RESERVED','RESERVATION_RELEASED','DELIVERY','LOSS','CORRECTION_ADD','CORRECTION_REMOVE')),
  CONSTRAINT ck_move_reason CHECK (movement_type NOT IN ('LOSS','CORRECTION_ADD','CORRECTION_REMOVE') OR CHAR_LENGTH(TRIM(COALESCE(reason,''))) > 0),
  CONSTRAINT fk_move_lot   FOREIGN KEY (lot_id) REFERENCES harvest_lots(lot_id),
  CONSTRAINT fk_move_unit  FOREIGN KEY (unit)   REFERENCES units(unit_code),
  CONSTRAINT fk_move_user  FOREIGN KEY (user_id) REFERENCES users(user_id),
  CONSTRAINT fk_move_alloc FOREIGN KEY (allocation_id) REFERENCES allocations(allocation_id),
  INDEX idx_moves_lot (lot_id)
) ENGINE=InnoDB;

CREATE TABLE delivery_receipts (
  receipt_id         INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  allocation_id      INT NOT NULL,
  allocated_quantity DECIMAL(12,3) NOT NULL,
  received_quantity  DECIMAL(12,3) NOT NULL,
  discrepancy        DECIMAL(12,3) NOT NULL COMMENT 'received - allocated (negative = shortfall)',
  discrepancy_reason VARCHAR(255) NULL,
  received_date      DATE NOT NULL,
  received_by        INT NOT NULL,
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_receipt_alloc UNIQUE (allocation_id),
  CONSTRAINT ck_rec_alloc CHECK (allocated_quantity > 0),
  CONSTRAINT ck_rec_recv  CHECK (received_quantity >= 0),
  CONSTRAINT ck_rec_diff  CHECK (ABS(discrepancy - (received_quantity - allocated_quantity)) < 0.0005),
  CONSTRAINT ck_rec_reason CHECK (ABS(discrepancy) < 0.0005 OR CHAR_LENGTH(TRIM(COALESCE(discrepancy_reason,''))) > 0),
  CONSTRAINT fk_rec_alloc FOREIGN KEY (allocation_id) REFERENCES allocations(allocation_id),
  CONSTRAINT fk_rec_user  FOREIGN KEY (received_by) REFERENCES users(user_id)
) ENGINE=InnoDB;

CREATE TABLE audit_log (
  audit_id    INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_id     INT NULL,
  username    VARCHAR(60) NULL,
  action      VARCHAR(40) NOT NULL,
  table_name  VARCHAR(40) NULL,
  record_id   VARCHAR(60) NULL,
  details     VARCHAR(500) NULL,
  success     TINYINT(1) NOT NULL DEFAULT 1,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(user_id),
  INDEX idx_audit_created (created_at)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------- triggers
DELIMITER $$

CREATE TRIGGER trg_audit_no_update BEFORE UPDATE ON audit_log FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Audit records cannot be modified or deleted.'; END$$

CREATE TRIGGER trg_audit_no_delete BEFORE DELETE ON audit_log FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Audit records cannot be modified or deleted.'; END$$

CREATE TRIGGER trg_moves_no_update BEFORE UPDATE ON stock_movements FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Stock movements cannot be modified; record a correction instead.'; END$$

CREATE TRIGGER trg_moves_no_delete BEFORE DELETE ON stock_movements FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Stock movements cannot be modified; record a correction instead.'; END$$

CREATE TRIGGER trg_lot_crop_matches_cycle BEFORE INSERT ON harvest_lots FOR EACH ROW
BEGIN
  DECLARE v_crop INT;
  SELECT crop_id INTO v_crop FROM crop_cycles WHERE cycle_id = NEW.cycle_id;
  IF v_crop IS NULL OR v_crop <> NEW.crop_id THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Harvest lot crop must match its crop cycle crop.';
  END IF;
END$$

-- Last line of defence for stock: no movement may overdraw a lot, even if application code is bypassed.
CREATE TRIGGER trg_movement_rules BEFORE INSERT ON stock_movements FOR EACH ROW
BEGIN
  DECLARE v_unit VARCHAR(20);
  DECLARE v_on_hand DECIMAL(14,3);
  DECLARE v_reserved DECIMAL(14,3);
  SELECT unit INTO v_unit FROM harvest_lots WHERE lot_id = NEW.lot_id;
  IF v_unit IS NULL OR NEW.unit <> v_unit THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Movement unit must match the harvest lot unit.';
  END IF;
  SELECT
    COALESCE(SUM(CASE movement_type WHEN 'HARVEST_ADDED' THEN quantity WHEN 'CORRECTION_ADD' THEN quantity
      WHEN 'DELIVERY' THEN -quantity WHEN 'LOSS' THEN -quantity WHEN 'CORRECTION_REMOVE' THEN -quantity ELSE 0 END), 0),
    COALESCE(SUM(CASE movement_type WHEN 'RESERVED' THEN quantity WHEN 'RESERVATION_RELEASED' THEN -quantity
      WHEN 'DELIVERY' THEN -quantity ELSE 0 END), 0)
  INTO v_on_hand, v_reserved FROM stock_movements WHERE lot_id = NEW.lot_id;
  IF NEW.movement_type IN ('RESERVED','LOSS','CORRECTION_REMOVE') AND NEW.quantity > (v_on_hand - v_reserved) + 0.0005 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Insufficient available stock in this lot for the requested quantity.';
  END IF;
  IF NEW.movement_type IN ('DELIVERY','RESERVATION_RELEASED') AND NEW.quantity > v_reserved + 0.0005 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Quantity exceeds the reserved stock of this lot.';
  END IF;
END$$

DELIMITER ;

-- ---------------------------------------------------------------- views
-- Current stock per lot, calculated from the movement ledger.
CREATE VIEW v_lot_stock AS
SELECT lot_id, unit, on_hand, reserved, ROUND(on_hand - reserved, 3) AS available
FROM (
  SELECT l.lot_id, l.unit,
    ROUND(COALESCE(SUM(CASE m.movement_type WHEN 'HARVEST_ADDED' THEN m.quantity WHEN 'CORRECTION_ADD' THEN m.quantity
      WHEN 'DELIVERY' THEN -m.quantity WHEN 'LOSS' THEN -m.quantity WHEN 'CORRECTION_REMOVE' THEN -m.quantity ELSE 0 END), 0), 3) AS on_hand,
    ROUND(COALESCE(SUM(CASE m.movement_type WHEN 'RESERVED' THEN m.quantity WHEN 'RESERVATION_RELEASED' THEN -m.quantity
      WHEN 'DELIVERY' THEN -m.quantity ELSE 0 END), 0), 3) AS reserved
  FROM harvest_lots l LEFT JOIN stock_movements m ON m.lot_id = l.lot_id
  GROUP BY l.lot_id, l.unit
) s;

CREATE VIEW v_lot_details AS
SELECT l.lot_id, l.cycle_id, l.crop_id, c.crop_name, cy.farm_id, f.farm_name, f.emirate,
  l.harvest_date, l.sell_by_date, l.quantity AS harvested_quantity, l.unit, l.is_active,
  s.on_hand, s.reserved, s.available,
  (SELECT COUNT(*) FROM harvest_lot_images i WHERE i.lot_id = l.lot_id AND i.is_active = 1) AS image_count
FROM harvest_lots l
JOIN crop_cycles cy ON cy.cycle_id = l.cycle_id
JOIN farms f ON f.farm_id = cy.farm_id
JOIN crops c ON c.crop_id = l.crop_id
JOIN v_lot_stock s ON s.lot_id = l.lot_id;

CREATE VIEW v_request_summary AS
SELECT r.request_id, r.market_id, mk.market_name, mk.emirate AS market_emirate,
  r.crop_id, c.crop_name, r.quantity AS requested, r.unit, r.needed_by_date,
  r.status, r.notes, r.created_by, r.created_at, r.updated_at,
  p.allocated_open, p.received,
  ROUND(GREATEST(r.quantity - p.allocated_open - p.received, 0), 3) AS remaining_need
FROM market_requests r
JOIN markets mk ON mk.market_id = r.market_id
JOIN crops c ON c.crop_id = r.crop_id
JOIN (
  SELECT r2.request_id,
    ROUND(COALESCE((SELECT SUM(a.quantity * ua.to_base_factor) FROM allocations a JOIN units ua ON ua.unit_code = a.unit
        WHERE a.request_id = r2.request_id AND a.status = 'ACTIVE'), 0) / ur.to_base_factor, 3) AS allocated_open,
    ROUND(COALESCE((SELECT SUM(d.received_quantity * ud.to_base_factor) FROM delivery_receipts d
        JOIN allocations a ON a.allocation_id = d.allocation_id JOIN units ud ON ud.unit_code = a.unit
        WHERE a.request_id = r2.request_id), 0) / ur.to_base_factor, 3) AS received
  FROM market_requests r2 JOIN units ur ON ur.unit_code = r2.unit
) p ON p.request_id = r.request_id;

CREATE VIEW v_allocations AS
SELECT a.allocation_id, a.request_id, a.lot_id, a.quantity, a.unit, a.status, a.allocated_by, a.allocated_at, a.closed_at,
  r.market_id, mk.market_name, c.crop_name, f.farm_name, cy.farm_id
FROM allocations a
JOIN market_requests r ON r.request_id = a.request_id
JOIN markets mk ON mk.market_id = r.market_id
JOIN harvest_lots l ON l.lot_id = a.lot_id
JOIN crops c ON c.crop_id = l.crop_id
JOIN crop_cycles cy ON cy.cycle_id = l.cycle_id
JOIN farms f ON f.farm_id = cy.farm_id;

CREATE VIEW v_movements AS
SELECT m.movement_id, m.lot_id, m.movement_type, m.quantity, m.unit, m.movement_date, m.user_id, m.reason, m.allocation_id,
  c.crop_name, f.farm_name, cy.farm_id, f.emirate, u.username
FROM stock_movements m
JOIN harvest_lots l ON l.lot_id = m.lot_id
JOIN crops c ON c.crop_id = l.crop_id
JOIN crop_cycles cy ON cy.cycle_id = l.cycle_id
JOIN farms f ON f.farm_id = cy.farm_id
LEFT JOIN users u ON u.user_id = m.user_id;

CREATE VIEW v_receipts AS
SELECT d.receipt_id, d.allocation_id, d.allocated_quantity, d.received_quantity, d.discrepancy, d.discrepancy_reason,
  d.received_date, d.received_by, a.request_id, a.lot_id, a.unit, c.crop_name, f.farm_name, cy.farm_id,
  r.market_id, mk.market_name, mk.emirate AS market_emirate
FROM delivery_receipts d
JOIN allocations a ON a.allocation_id = d.allocation_id
JOIN market_requests r ON r.request_id = a.request_id
JOIN markets mk ON mk.market_id = r.market_id
JOIN harvest_lots l ON l.lot_id = a.lot_id
JOIN crops c ON c.crop_id = l.crop_id
JOIN crop_cycles cy ON cy.cycle_id = l.cycle_id
JOIN farms f ON f.farm_id = cy.farm_id;

CREATE VIEW v_cycles AS
SELECT cy.cycle_id, cy.farm_id, cy.crop_id, cy.planting_date, cy.expected_harvest_date, cy.expected_quantity,
  cy.expected_unit, cy.status, cy.notes, cy.is_active, c.crop_name, f.farm_name, f.emirate
FROM crop_cycles cy JOIN crops c ON c.crop_id = cy.crop_id JOIN farms f ON f.farm_id = cy.farm_id;

CREATE VIEW v_users AS
SELECT u.user_id, u.username, u.full_name, u.role, u.market_id, m.market_name, u.is_active,
  u.failed_attempts, u.locked_until, u.created_at,
  (SELECT GROUP_CONCAT(f.farm_name ORDER BY f.farm_name SEPARATOR ', ')
     FROM user_farms uf JOIN farms f ON f.farm_id = uf.farm_id WHERE uf.user_id = u.user_id) AS farms
FROM users u LEFT JOIN markets m ON m.market_id = u.market_id;

-- =============================================================================
-- Local Farm and Market Food Availability System  (COSC444)
-- Sample (fictional) data. Dates are RELATIVE to the day this script is run, so the
-- demonstration data is always fresh (nothing is expired on demo day).
-- Demo accounts: admin1, farmer_ahmed, farmer_mariam, farmer_salem,
--                buyer_dubai, buyer_adcm, buyer_sharjah, buyer_alain   (password: Demo@1234)
-- =============================================================================

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
