 Example 1 – User Greeting

Request:

{
  "session_id": "support-001",
  "message": "hello"
}


Response:

{
  "session_id": "support-001",
  "reply": "Hello there! How can I assist you today? You can ask about LED panels, controllers, or any support issue.",
  "intent": "greeting"
}

 Example 2 – Asking About Products

Request:

{
  "session_id": "support-001",
  "message": "What LED panels do you have?"
}


Response:

{
  "session_id": "support-001",
  "reply": "We currently offer panels P1 through P10 — each suited for different pixel pitches and brightness needs. Would you like to know the specs or pricing details?",
  "intent": "product_inquiry"
}

 Example 3 – Asking About Controllers

Request:

{
  "session_id": "support-001",
  "message": "what are the available controllers?"
}


Response:

{
  "session_id": "support-001",
  "reply": "We support controllers such as Novastar, Colorlight, and VDWall series — compatible with both indoor and outdoor LED displays.",
  "intent": "controller_info"
}

 Example 4 – Asking About Accessories

Request:

{
  "session_id": "support-001",
  "message": "Do you have spare parts or cables?"
}


Response:

{
  "session_id": "support-001",
  "reply": "Yes, we provide accessories like power cables, signal cables, connectors, and mounting kits for LED panels.",
  "intent": "accessory_info"
}

 Example 5 – Reporting a Technical Issue

Request:

{
  "session_id": "support-001",
  "message": "my panel screen is flickering"
}


Response:

{
  "session_id": "support-001",
  "reply": "It seems like a refresh or power supply issue. Please check your controller connection and power input. Would you like to create a support ticket?",
  "intent": "issue_diagnosis"
}

 Example 6 – Asking About Maintenance

Request:

{
  "session_id": "support-001",
  "message": "How often should I clean the LED panels?"
}


Response:

{
  "session_id": "support-001",
  "reply": "For optimal performance, clean LED panels once every 2–4 weeks using a dry microfiber cloth and ensure the power is off before cleaning.",
  "intent": "maintenance_guide"
}

 Example 7 – General Knowledge or Company Info

Request:

{
  "session_id": "support-001",
  "message": "Who is the manufacturer of your LED panels?"
}


Response:

{
  "session_id": "support-001",
  "reply": "Our panels are manufactured under XIGI Tech Pvt Ltd with high-quality LED modules sourced from trusted suppliers in Taiwan and China.",
  "intent": "company_info"
}




