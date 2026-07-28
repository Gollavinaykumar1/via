# backend/routers/template_router.py — VIA Phase 3: Smart Task Templates

from fastapi import APIRouter, Depends
from backend.auth.auth import get_current_active_user

router = APIRouter(prefix="/templates", tags=["Templates"])

TASK_TEMPLATES = [
    {
        "id": "saas-app",
        "category": "Product",
        "icon": "🚀",
        "title": "SaaS Web Application",
        "description": "Full-stack SaaS with auth, subscription billing, dashboard, and API",
        "task": "Build a complete SaaS web application with user authentication, subscription billing with Stripe, user dashboard, REST API, admin panel, and PostgreSQL database. Include email verification, password reset, and role-based access control.",
        "departments": ["backend", "frontend", "security", "devops"],
        "estimated_time": "8-12 min",
        "complexity": "High",
        "color": "c",
    },
    {
        "id": "ecommerce",
        "category": "Product",
        "icon": "🛒",
        "title": "E-Commerce Platform",
        "description": "Online store with products, cart, checkout, and order management",
        "task": "Build a complete e-commerce platform with product catalog, shopping cart, secure checkout with payment integration, order management system, inventory tracking, customer accounts, and admin dashboard with analytics.",
        "departments": ["backend", "frontend", "security", "devops", "marketing"],
        "estimated_time": "10-15 min",
        "complexity": "High",
        "color": "v2",
    },
    {
        "id": "ai-chatbot",
        "category": "AI",
        "icon": "🤖",
        "title": "AI Chatbot Platform",
        "description": "Intelligent chatbot with custom training, multi-channel deployment",
        "task": "Build an AI-powered chatbot platform with custom knowledge base training, multi-channel deployment (web widget, WhatsApp, Slack), conversation history, analytics dashboard, and admin interface for bot configuration.",
        "departments": ["backend", "frontend", "ai_research", "devops"],
        "estimated_time": "8-12 min",
        "complexity": "High",
        "color": "m2",
    },
    {
        "id": "task-manager",
        "category": "Productivity",
        "icon": "✅",
        "title": "Project Task Manager",
        "description": "Kanban-style task manager with teams, deadlines, and notifications",
        "task": "Build a project management tool with kanban boards, task assignment, deadline tracking, team collaboration, file attachments, comment threads, email notifications, and productivity analytics dashboard.",
        "departments": ["backend", "frontend", "devops"],
        "estimated_time": "5-8 min",
        "complexity": "Medium",
        "color": "g",
    },
    {
        "id": "blog-cms",
        "category": "Content",
        "icon": "📝",
        "title": "Blog & CMS Platform",
        "description": "Full-featured blog with CMS, SEO optimization, and analytics",
        "task": "Build a blog and content management system with rich text editor, SEO optimization tools, image management, categories and tags, comments system, newsletter integration, social sharing, and traffic analytics.",
        "departments": ["backend", "frontend", "devops", "marketing"],
        "estimated_time": "5-8 min",
        "complexity": "Medium",
        "color": "y",
    },
    {
        "id": "hospital-mgmt",
        "category": "Healthcare",
        "icon": "🏥",
        "title": "Hospital Management System",
        "description": "Patient records, appointments, billing, and doctor portal",
        "task": "Build a hospital management system with patient registration, appointment scheduling, doctor portal, medical records management, prescription tracking, billing and insurance processing, and department dashboards.",
        "departments": ["backend", "frontend", "security", "devops"],
        "estimated_time": "10-14 min",
        "complexity": "High",
        "color": "m",
    },
    {
        "id": "fintech-app",
        "category": "Finance",
        "icon": "💳",
        "title": "FinTech Mobile App",
        "description": "Digital wallet, transfers, spending analytics, and budgeting",
        "task": "Build a fintech application with digital wallet, peer-to-peer transfers, spending analytics, budget planning, bill payments, transaction history, fraud detection alerts, and multi-currency support.",
        "departments": ["backend", "frontend", "security", "ai_research", "devops"],
        "estimated_time": "12-18 min",
        "complexity": "Very High",
        "color": "g2",
    },
    {
        "id": "social-network",
        "category": "Social",
        "icon": "🌐",
        "title": "Social Network Platform",
        "description": "User profiles, posts, followers, messaging, and feed algorithm",
        "task": "Build a social networking platform with user profiles, post sharing with media, follow/unfollow system, algorithmic feed, direct messaging, notifications, hashtags, trending topics, and content moderation tools.",
        "departments": ["backend", "frontend", "ai_research", "devops", "security"],
        "estimated_time": "12-18 min",
        "complexity": "Very High",
        "color": "v",
    },
    {
        "id": "inventory-system",
        "category": "Business",
        "icon": "📦",
        "title": "Inventory Management",
        "description": "Stock tracking, suppliers, purchase orders, and warehouse management",
        "task": "Build an inventory management system with real-time stock tracking, supplier management, purchase order processing, barcode scanning support, low stock alerts, warehouse location mapping, and comprehensive reporting.",
        "departments": ["backend", "frontend", "devops"],
        "estimated_time": "6-9 min",
        "complexity": "Medium",
        "color": "o",
    },
    {
        "id": "learning-platform",
        "category": "Education",
        "icon": "🎓",
        "title": "Online Learning Platform",
        "description": "Course creation, video lessons, quizzes, and student progress tracking",
        "task": "Build an online learning platform with course creation tools, video lesson hosting, interactive quizzes, student progress tracking, certificate generation, instructor dashboard, payment processing, and discussion forums.",
        "departments": ["backend", "frontend", "ai_research", "devops", "marketing"],
        "estimated_time": "10-14 min",
        "complexity": "High",
        "color": "c",
    },
    {
        "id": "restaurant-app",
        "category": "Food",
        "icon": "🍽️",
        "title": "Restaurant Management App",
        "description": "Table booking, digital menu, orders, kitchen display, and billing",
        "task": "Build a restaurant management application with table reservation system, digital menu with photos, order management, kitchen display system, bill splitting, loyalty program, delivery tracking, and staff management portal.",
        "departments": ["backend", "frontend", "devops"],
        "estimated_time": "6-10 min",
        "complexity": "Medium",
        "color": "m2",
    },
    {
        "id": "real-estate",
        "category": "Property",
        "icon": "🏠",
        "title": "Real Estate Platform",
        "description": "Property listings, virtual tours, mortgage calculator, and agent portal",
        "task": "Build a real estate platform with property listings with rich media, virtual tour integration, advanced search and filters, mortgage calculator, agent profiles and chat, saved properties, and market analytics dashboard.",
        "departments": ["backend", "frontend", "devops", "marketing"],
        "estimated_time": "8-12 min",
        "complexity": "High",
        "color": "g",
    },
]


@router.get("/")
async def list_templates(current_user: dict = Depends(get_current_active_user)):
    """Get all available task templates."""
    return {
        "templates": TASK_TEMPLATES,
        "total": len(TASK_TEMPLATES),
        "categories": list({t["category"] for t in TASK_TEMPLATES}),
    }


@router.get("/{template_id}/")
async def get_template(template_id: str, current_user: dict = Depends(get_current_active_user)):
    """Get a specific task template by ID."""
    for t in TASK_TEMPLATES:
        if t["id"] == template_id:
            return t
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Template not found")


@router.get("/category/{category}/")
async def get_templates_by_category(category: str, current_user: dict = Depends(get_current_active_user)):
    """Get templates filtered by category."""
    filtered = [t for t in TASK_TEMPLATES if t["category"].lower() == category.lower()]
    return {"templates": filtered, "total": len(filtered)}
