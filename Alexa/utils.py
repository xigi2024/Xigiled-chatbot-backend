from .models import KnowledgeBase, Product
import random

def get_ai_response(user_message):
    user_message = user_message.lower()

    # Check for product mentions
    product_matches = Product.objects.filter(name__icontains=user_message)
    if product_matches.exists():
        product = product_matches.first()
        return (
            f"Our {product.name} is one of the best choices for "
            f"{product.category or 'various installations'}. "
            f"Specs: {product.specifications or 'Details coming soon.'}"
        )

    # Check for knowledgebase entries
    kb_entry = KnowledgeBase.objects.filter(question__icontains=user_message).first()
    if kb_entry:
        return kb_entry.answer

    # General fallback replies
    generic_responses = [
        "I’m Alexa, your LED assistant. Could you please clarify what you’re looking for?",
        "We specialize in LED video walls for events, retail, and government spaces.",
        "Would you like to know about indoor or outdoor LED displays?",
        "You can ask me about product specs, maintenance, or installation help anytime!"
    ]
    return random.choice(generic_responses)