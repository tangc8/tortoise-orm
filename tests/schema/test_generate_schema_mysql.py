import re

from asynctest.mock import CoroutineMock, patch

from tests.schema.test_generate_schema import TestGenerateSchema
from tortoise import Tortoise
from tortoise.contrib import test
from tortoise.utils import get_schema_sql


class TestGenerateSchemaMySQL(TestGenerateSchema):
    async def init_for(self, module: str, safe=False) -> None:
        try:
            with patch("aiomysql.create_pool", new=CoroutineMock()):
                await Tortoise.init(
                    {
                        "connections": {
                            "default": {
                                "engine": "tortoise.backends.mysql",
                                "credentials": {
                                    "database": "test",
                                    "host": "127.0.0.1",
                                    "password": "foomip",
                                    "port": 3306,
                                    "user": "root",
                                    "connect_timeout": 1.5,
                                    "charset": "utf8mb4",
                                },
                            }
                        },
                        "apps": {"models": {"models": [module], "default_connection": "default"}},
                    }
                )
                self.sqls = get_schema_sql(Tortoise._connections["default"], safe).split("; ")
        except ImportError:
            raise test.SkipTest("aiomysql not installed")

    async def test_noid(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql("`noid`")
        self.assertIn("`name` VARCHAR(255)", sql)
        self.assertIn("`id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT", sql)

    async def test_create_index(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql("KEY")
        self.assertIsNotNone(re.search(r"idx_tournament_created_\w+", sql))

    async def test_minrelation(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql("`minrelation`")
        self.assertIn("`tournament_id` SMALLINT NOT NULL,", sql)
        self.assertIn(
            "FOREIGN KEY (`tournament_id`) REFERENCES `tournament` (`id`) ON DELETE CASCADE", sql
        )
        self.assertNotIn("participants", sql)

        sql = self.get_sql("`minrelation_team`")
        self.assertIn("`minrelation_id` INT NOT NULL", sql)
        self.assertIn(
            "FOREIGN KEY (`minrelation_id`) REFERENCES `minrelation` (`id`) ON DELETE CASCADE", sql
        )
        self.assertIn("`team_id` INT NOT NULL", sql)
        self.assertIn("FOREIGN KEY (`team_id`) REFERENCES `team` (`id`) ON DELETE CASCADE", sql)

    async def test_table_and_row_comment_generation(self):
        await self.init_for("tests.testmodels")
        sql = self.get_sql("comments")
        self.assertIn("COMMENT='Test Table comment'", sql)
        self.assertIn("COMMENT 'This column acts as it\\'s own comment'", sql)
        self.assertRegex(sql, r".*\\n.*")
        self.assertRegex(sql, r".*it\\'s.*")

    async def test_schema(self):
        self.maxDiff = None
        await self.init_for("tests.schema.models_schema_create")
        sql = get_schema_sql(Tortoise.get_connection("default"), safe=False)
        self.assertEqual(
            sql.strip(),
            """
CREATE TABLE `company` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` LONGTEXT NOT NULL,
    `uuid` CHAR(36) NOT NULL UNIQUE
) CHARACTER SET utf8mb4;
CREATE TABLE `defaultpk` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `val` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE `employee` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` LONGTEXT NOT NULL,
    `company_id` CHAR(36) NOT NULL,
    CONSTRAINT `fk_employee_company_08999a42` FOREIGN KEY (`company_id`) REFERENCES `company` (`uuid`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE `inheritedmodel` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `zero` INT NOT NULL,
    `one` VARCHAR(40),
    `new_field` VARCHAR(100) NOT NULL,
    `two` VARCHAR(40) NOT NULL,
    `name` LONGTEXT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE `sometable` (
    `sometable_id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `some_chars_table` VARCHAR(255) NOT NULL,
    `fk_sometable` INT,
    CONSTRAINT `fk_sometabl_sometabl_6efae9bd` FOREIGN KEY (`fk_sometable`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE,
    KEY `idx_sometable_some_ch_3d69eb` (`some_chars_table`)
) CHARACTER SET utf8mb4;
CREATE TABLE `team` (
    `name` VARCHAR(50) NOT NULL  PRIMARY KEY COMMENT 'The TEAM name (and PK)',
    `key` INT NOT NULL,
    `manager_id` VARCHAR(50),
    CONSTRAINT `fk_team_team_9c77cd8f` FOREIGN KEY (`manager_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    KEY `idx_team_manager_676134` (`manager_id`, `key`),
    KEY `idx_team_manager_ef8f69` (`manager_id`, `name`)
) CHARACTER SET utf8mb4 COMMENT='The TEAMS!';
CREATE TABLE `teamaddress` (
    `city` VARCHAR(50) NOT NULL  COMMENT 'City',
    `country` VARCHAR(50) NOT NULL  COMMENT 'Country',
    `street` VARCHAR(128) NOT NULL  COMMENT 'Street Address',
    `team_id` VARCHAR(50) NOT NULL  PRIMARY KEY,
    CONSTRAINT `fk_teamaddr_team_1c78d737` FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='The Team\\'s address';
CREATE TABLE `tournament` (
    `tid` SMALLINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL  COMMENT 'Tournament name',
    `created` DATETIME(6) NOT NULL  COMMENT 'Created */\\'`/* datetime' DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_tournament_name_6fe200` (`name`)
) CHARACTER SET utf8mb4 COMMENT='What Tournaments */\\'`/* we have';
CREATE TABLE `event` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT 'Event ID',
    `name` LONGTEXT NOT NULL,
    `modified` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `prize` DECIMAL(10,2),
    `token` VARCHAR(100) NOT NULL UNIQUE COMMENT 'Unique token',
    `key` VARCHAR(100) NOT NULL,
    `tournament_id` SMALLINT NOT NULL COMMENT 'FK to tournament',
    UNIQUE KEY `uid_event_name_c6f89f` (`name`, `prize`),
    UNIQUE KEY `uid_event_tournam_a5b730` (`tournament_id`, `key`),
    CONSTRAINT `fk_event_tourname_51c2b82d` FOREIGN KEY (`tournament_id`) REFERENCES `tournament` (`tid`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='This table contains a list of all the events';
CREATE TABLE `venueinformation` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(128) NOT NULL,
    `capacity` INT NOT NULL  COMMENT 'No. of seats',
    `rent` DOUBLE NOT NULL,
    `team_id` VARCHAR(50)  UNIQUE,
    CONSTRAINT `fk_venueinf_team_198af929` FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
CREATE TABLE `sometable_self` (
    `backward_sts` INT NOT NULL,
    `sts_forward` INT NOT NULL,
    FOREIGN KEY (`backward_sts`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE,
    FOREIGN KEY (`sts_forward`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE `team_team` (
    `team_rel_id` VARCHAR(50) NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    FOREIGN KEY (`team_rel_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE `teamevents` (
    `event_id` BIGINT NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    FOREIGN KEY (`event_id`) REFERENCES `event` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='How participants relate';
""".strip(),
        )

    async def test_schema_safe(self):
        self.maxDiff = None
        await self.init_for("tests.schema.models_schema_create")
        sql = get_schema_sql(Tortoise.get_connection("default"), safe=True)

        self.assertEqual(
            sql.strip(),
            """
CREATE TABLE IF NOT EXISTS `company` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` LONGTEXT NOT NULL,
    `uuid` CHAR(36) NOT NULL UNIQUE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `defaultpk` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `val` INT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `employee` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` LONGTEXT NOT NULL,
    `company_id` CHAR(36) NOT NULL,
    CONSTRAINT `fk_employee_company_08999a42` FOREIGN KEY (`company_id`) REFERENCES `company` (`uuid`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `inheritedmodel` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `zero` INT NOT NULL,
    `one` VARCHAR(40),
    `new_field` VARCHAR(100) NOT NULL,
    `two` VARCHAR(40) NOT NULL,
    `name` LONGTEXT NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sometable` (
    `sometable_id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `some_chars_table` VARCHAR(255) NOT NULL,
    `fk_sometable` INT,
    CONSTRAINT `fk_sometabl_sometabl_6efae9bd` FOREIGN KEY (`fk_sometable`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE,
    KEY `idx_sometable_some_ch_3d69eb` (`some_chars_table`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `team` (
    `name` VARCHAR(50) NOT NULL  PRIMARY KEY COMMENT 'The TEAM name (and PK)',
    `key` INT NOT NULL,
    `manager_id` VARCHAR(50),
    CONSTRAINT `fk_team_team_9c77cd8f` FOREIGN KEY (`manager_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    KEY `idx_team_manager_676134` (`manager_id`, `key`),
    KEY `idx_team_manager_ef8f69` (`manager_id`, `name`)
) CHARACTER SET utf8mb4 COMMENT='The TEAMS!';
CREATE TABLE IF NOT EXISTS `teamaddress` (
    `city` VARCHAR(50) NOT NULL  COMMENT 'City',
    `country` VARCHAR(50) NOT NULL  COMMENT 'Country',
    `street` VARCHAR(128) NOT NULL  COMMENT 'Street Address',
    `team_id` VARCHAR(50) NOT NULL  PRIMARY KEY,
    CONSTRAINT `fk_teamaddr_team_1c78d737` FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='The Team\\'s address';
CREATE TABLE IF NOT EXISTS `tournament` (
    `tid` SMALLINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL  COMMENT 'Tournament name',
    `created` DATETIME(6) NOT NULL  COMMENT 'Created */\\'`/* datetime' DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_tournament_name_6fe200` (`name`)
) CHARACTER SET utf8mb4 COMMENT='What Tournaments */\\'`/* we have';
CREATE TABLE IF NOT EXISTS `event` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT 'Event ID',
    `name` LONGTEXT NOT NULL,
    `modified` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `prize` DECIMAL(10,2),
    `token` VARCHAR(100) NOT NULL UNIQUE COMMENT 'Unique token',
    `key` VARCHAR(100) NOT NULL,
    `tournament_id` SMALLINT NOT NULL COMMENT 'FK to tournament',
    UNIQUE KEY `uid_event_name_c6f89f` (`name`, `prize`),
    UNIQUE KEY `uid_event_tournam_a5b730` (`tournament_id`, `key`),
    CONSTRAINT `fk_event_tourname_51c2b82d` FOREIGN KEY (`tournament_id`) REFERENCES `tournament` (`tid`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='This table contains a list of all the events';
CREATE TABLE IF NOT EXISTS `venueinformation` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(128) NOT NULL,
    `capacity` INT NOT NULL  COMMENT 'No. of seats',
    `rent` DOUBLE NOT NULL,
    `team_id` VARCHAR(50)  UNIQUE,
    CONSTRAINT `fk_venueinf_team_198af929` FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `sometable_self` (
    `backward_sts` INT NOT NULL,
    `sts_forward` INT NOT NULL,
    FOREIGN KEY (`backward_sts`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE,
    FOREIGN KEY (`sts_forward`) REFERENCES `sometable` (`sometable_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `team_team` (
    `team_rel_id` VARCHAR(50) NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    FOREIGN KEY (`team_rel_id`) REFERENCES `team` (`name`) ON DELETE CASCADE,
    FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `teamevents` (
    `event_id` BIGINT NOT NULL,
    `team_id` VARCHAR(50) NOT NULL,
    FOREIGN KEY (`event_id`) REFERENCES `event` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`team_id`) REFERENCES `team` (`name`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='How participants relate';
""".strip(),
        )
