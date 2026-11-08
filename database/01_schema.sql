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
