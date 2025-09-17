"""
Database test script for DebtEase application.
Tests database connection, schema creation, and basic CRUD operations.
"""

import asyncio
import logging
import sys
from datetime import date, datetime
from typing import Dict, Any
from app.databases.database import db_manager
from app.databases.migrations.migration_runner import init_database_schema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_connection() -> bool:
    """Test basic database connectivity."""
    logger.info("Testing database connection...")
    try:
        result = await db_manager.test_connection()
        if result:
            logger.info("✓ Database connection successful")
            return True
        else:
            logger.error("✗ Database connection failed")
            return False
    except Exception as e:
        logger.error(f"✗ Database connection error: {e}")
        return False


async def test_schema_creation() -> bool:
    """Test database schema creation by running migrations."""
    logger.info("Testing schema creation...")
    try:
        await init_database_schema()
        logger.info("✓ Database schema created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Schema creation failed: {e}")
        return False


async def test_table_existence() -> bool:
    """Test that all required tables exist."""
    logger.info("Testing table existence...")
    
    expected_tables = [
        'users', 'debts', 'payment_history', 'ai_recommendations',
        'user_streaks', 'repayment_plans', 'notifications', 'schema_migrations'
    ]
    
    try:
        async with db_manager.get_connection() as conn:
            # Get list of tables
            tables_result = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE';
            """)
            
            existing_tables = {row['table_name'] for row in tables_result}
            
            missing_tables = set(expected_tables) - existing_tables
            if missing_tables:
                logger.error(f"✗ Missing tables: {missing_tables}")
                return False
            
            logger.info(f"✓ All {len(expected_tables)} tables exist")
            return True
            
    except Exception as e:
        logger.error(f"✗ Table existence check failed: {e}")
        return False


async def test_basic_crud_operations() -> bool:
    """Test basic CRUD operations on all tables."""
    logger.info("Testing basic CRUD operations...")
    
    try:
        async with db_manager.get_connection() as conn:
            # Test Users table
            logger.info("  Testing Users table...")
            
            # Create a test user
            user_result = await conn.fetchrow("""
                INSERT INTO users (email, full_name, monthly_income, password_hash)
                VALUES ($1, $2, $3, $4)
                RETURNING id;
            """, "test@debtease.com", "Test User", 5000.00, "hashed_password_123")
            
            user_id = user_result['id']
            logger.info(f"    ✓ Created user with ID: {user_id}")
            
            # Test Debts table
            logger.info("  Testing Debts table...")
            
            debt_result = await conn.fetchrow("""
                INSERT INTO debts (
                    user_id, name, debt_type, principal_amount, current_balance,
                    interest_rate, minimum_payment, lender
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id;
            """, user_id, "Test Credit Card", "credit_card", 10000.00, 8500.00, 18.99, 250.00, "Test Bank")
            
            debt_id = debt_result['id']
            logger.info(f"    ✓ Created debt with ID: {debt_id}")
            
            # Test Payment History table
            logger.info("  Testing Payment History table...")
            
            payment_result = await conn.fetchrow("""
                INSERT INTO payment_history (
                    debt_id, user_id, amount, payment_date, principal_portion, interest_portion
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id;
            """, debt_id, user_id, 300.00, date.today(), 150.00, 150.00)
            
            payment_id = payment_result['id']
            logger.info(f"    ✓ Created payment with ID: {payment_id}")
            
            # Test AI Recommendations table
            logger.info("  Testing AI Recommendations table...")
            
            rec_result = await conn.fetchrow("""
                INSERT INTO ai_recommendations (
                    user_id, recommendation_type, title, description, potential_savings, priority_score
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id;
            """, user_id, "avalanche", "Pay high-interest debt first", 
                "Focus on credit card with 18.99% APR", 1200.00, 8)
            
            rec_id = rec_result['id']
            logger.info(f"    ✓ Created recommendation with ID: {rec_id}")
            
            # Test User Streaks table
            logger.info("  Testing User Streaks table...")
            
            streak_result = await conn.fetchrow("""
                INSERT INTO user_streaks (
                    user_id, current_streak, longest_streak, total_payments_logged
                )
                VALUES ($1, $2, $3, $4)
                RETURNING id;
            """, user_id, 5, 10, 25)
            
            streak_id = streak_result['id']
            logger.info(f"    ✓ Created streak record with ID: {streak_id}")
            
            # Test Repayment Plans table
            logger.info("  Testing Repayment Plans table...")
            
            plan_result = await conn.fetchrow("""
                INSERT INTO repayment_plans (
                    user_id, strategy, monthly_payment_amount, total_interest_saved
                )
                VALUES ($1, $2, $3, $4)
                RETURNING id;
            """, user_id, "avalanche", 500.00, 2400.00)
            
            plan_id = plan_result['id']
            logger.info(f"    ✓ Created repayment plan with ID: {plan_id}")
            
            # Test Notifications table
            logger.info("  Testing Notifications table...")
            
            notif_result = await conn.fetchrow("""
                INSERT INTO notifications (
                    user_id, type, title, message
                )
                VALUES ($1, $2, $3, $4)
                RETURNING id;
            """, user_id, "payment_reminder", "Payment Due Soon", "Your credit card payment is due in 3 days")
            
            notif_id = notif_result['id']
            logger.info(f"    ✓ Created notification with ID: {notif_id}")
            
            # Test READ operations
            logger.info("  Testing READ operations...")
            
            # Read user with debts
            user_with_debts = await conn.fetch("""
                SELECT u.*, d.name as debt_name, d.current_balance
                FROM users u
                LEFT JOIN debts d ON u.id = d.user_id
                WHERE u.id = $1;
            """, user_id)
            
            logger.info(f"    ✓ Read user with {len(user_with_debts)} debt records")
            
            # Test UPDATE operations
            logger.info("  Testing UPDATE operations...")
            
            await conn.execute("""
                UPDATE debts SET current_balance = $1 WHERE id = $2;
            """, 8200.00, debt_id)
            
            logger.info("    ✓ Updated debt balance")
            
            # Test DELETE operations (clean up test data)
            logger.info("  Cleaning up test data...")
            
            # Delete in proper order due to foreign key constraints
            await conn.execute("DELETE FROM notifications WHERE user_id = $1", user_id)
            await conn.execute("DELETE FROM repayment_plans WHERE user_id = $1", user_id)
            await conn.execute("DELETE FROM user_streaks WHERE user_id = $1", user_id)
            await conn.execute("DELETE FROM ai_recommendations WHERE user_id = $1", user_id)
            await conn.execute("DELETE FROM payment_history WHERE user_id = $1", user_id)
            await conn.execute("DELETE FROM debts WHERE user_id = $1", user_id)
            await conn.execute("DELETE FROM users WHERE id = $1", user_id)
            
            logger.info("    ✓ Cleaned up test data")
            
        logger.info("✓ All CRUD operations successful")
        return True
        
    except Exception as e:
        logger.error(f"✗ CRUD operations failed: {e}")
        return False


async def test_database_constraints() -> bool:
    """Test that database constraints are working properly."""
    logger.info("Testing database constraints...")
    
    try:
        async with db_manager.get_connection() as conn:
            # Test email uniqueness constraint
            logger.info("  Testing email uniqueness constraint...")
            
            # Create first user
            await conn.execute("""
                INSERT INTO users (email, password_hash)
                VALUES ($1, $2);
            """, "unique@test.com", "password123")
            
            # Try to create duplicate email - should fail
            try:
                await conn.execute("""
                    INSERT INTO users (email, password_hash)
                    VALUES ($1, $2);
                """, "unique@test.com", "password456")
                logger.error("    ✗ Duplicate email constraint not working")
                return False
            except Exception:
                logger.info("    ✓ Email uniqueness constraint working")
            
            # Clean up
            await conn.execute("DELETE FROM users WHERE email = $1", "unique@test.com")
            
            # Test positive amount constraints
            logger.info("  Testing positive amount constraints...")
            
            # Create a user for testing
            user_result = await conn.fetchrow("""
                INSERT INTO users (email, password_hash)
                VALUES ($1, $2)
                RETURNING id;
            """, "constraint@test.com", "password123")
            
            user_id = user_result['id']
            
            # Try to create debt with negative amount - should fail
            try:
                await conn.execute("""
                    INSERT INTO debts (
                        user_id, name, debt_type, principal_amount, 
                        current_balance, interest_rate, minimum_payment, lender
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
                """, user_id, "Test Debt", "credit_card", -1000.00, 500.00, 10.0, 50.00, "Test Bank")
                logger.error("    ✗ Negative amount constraint not working")
                return False
            except Exception:
                logger.info("    ✓ Positive amount constraint working")
            
            # Clean up
            await conn.execute("DELETE FROM users WHERE id = $1", user_id)
            
        logger.info("✓ All constraint tests passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Constraint tests failed: {e}")
        return False


async def run_all_tests() -> Dict[str, bool]:
    """Run all database tests and return results."""
    logger.info("Starting comprehensive database tests...")
    
    results = {}
    
    # Test 1: Database Connection
    results['connection'] = await test_database_connection()
    
    # Test 2: Schema Creation
    if results['connection']:
        results['schema'] = await test_schema_creation()
    else:
        results['schema'] = False
        logger.error("Skipping schema tests due to connection failure")
    
    # Test 3: Table Existence
    if results['schema']:
        results['tables'] = await test_table_existence()
    else:
        results['tables'] = False
        logger.error("Skipping table tests due to schema failure")
    
    # Test 4: CRUD Operations
    if results['tables']:
        results['crud'] = await test_basic_crud_operations()
    else:
        results['crud'] = False
        logger.error("Skipping CRUD tests due to table failure")
    
    # Test 5: Database Constraints
    if results['tables']:
        results['constraints'] = await test_database_constraints()
    else:
        results['constraints'] = False
        logger.error("Skipping constraint tests due to table failure")
    
    return results


async def main():
    """Main test runner."""
    logger.info("=" * 60)
    logger.info("DebtEase Database Test Suite")
    logger.info("=" * 60)
    
    results = await run_all_tests()
    
    logger.info("=" * 60)
    logger.info("Test Results Summary:")
    logger.info("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{test_name.capitalize():15} {status}")
        if not passed:
            all_passed = False
    
    logger.info("=" * 60)
    
    if all_passed:
        logger.info("🎉 All tests passed! Database setup is successful.")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed. Please check the database setup.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
