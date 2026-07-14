import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app import models, schemas

# Helper to resolve HCP by name (fuzzy case-insensitive match)
def resolve_hcp(db: Session, name: str) -> models.HCP:
    # Try exact match first
    hcp = db.query(models.HCP).filter(models.HCP.name == name).first()
    if hcp:
        return hcp
    
    # Try case-insensitive exact match
    hcp = db.query(models.HCP).filter(models.HCP.name.ilike(name)).first()
    if hcp:
        return hcp
    
    # Try cleaning titlePrefix like "Dr." or "Dr. "
    clean_name = name.replace("Dr.", "").replace("Dr", "").strip()
    
    # Try searching for substring in database names
    hcp = db.query(models.HCP).filter(
        or_(
            models.HCP.name.ilike(f"%{clean_name}%"),
            models.HCP.name.ilike(f"%{name}%")
        )
    ).first()
    
    if not hcp:
        # Fetch all available to guide the LLM/User
        all_hcps = db.query(models.HCP).all()
        hcp_names = ", ".join([h.name for h in all_hcps])
        raise ValueError(
            f"HCP '{name}' could not be resolved. "
            f"Please choose from available HCPs: {hcp_names}"
        )
    return hcp

# Helper to resolve Product by name
def resolve_product(db: Session, name: str) -> models.Product:
    # Try exact or substring
    product = db.query(models.Product).filter(
        or_(
            models.Product.name == name,
            models.Product.name.ilike(name),
            models.Product.name.ilike(f"%{name}%")
        )
    ).first()
    if not product:
        all_products = db.query(models.Product).all()
        prod_names = ", ".join([p.name for p in all_products])
        raise ValueError(
            f"Product '{name}' could not be resolved. "
            f"Available products: {prod_names}"
        )
    return product

# Helper to resolve Material by name
def resolve_material(db: Session, name: str) -> models.Material:
    material = db.query(models.Material).filter(
        or_(
            models.Material.name == name,
            models.Material.name.ilike(name),
            models.Material.name.ilike(f"%{name}%")
        )
    ).first()
    if not material:
        all_materials = db.query(models.Material).all()
        mat_names = ", ".join([m.name for m in all_materials])
        raise ValueError(
            f"Material '{name}' could not be resolved. "
            f"Available materials: {mat_names}"
        )
    return material

# Helper to resolve Sample by name
def resolve_sample(db: Session, name: str) -> models.Sample:
    sample = db.query(models.Sample).filter(
        or_(
            models.Sample.name == name,
            models.Sample.name.ilike(name),
            models.Sample.name.ilike(f"%{name}%")
        )
    ).first()
    if not sample:
        all_samples = db.query(models.Sample).all()
        sample_names = ", ".join([s.name for s in all_samples])
        raise ValueError(
            f"Sample '{name}' could not be resolved. "
            f"Available samples: {sample_names}"
        )
    return sample


def log_interaction_transactional(db: Session, data: schemas.LogInteractionInput) -> models.Interaction:
    """
    Creates a new interaction record transactionally.
    If sample inventory validation fails, the entire transaction is rolled back.
    """
    try:
        # 1. Resolve HCP
        hcp = resolve_hcp(db, data.hcp_name)
        
        # 2. Parse Date and Time
        parsed_date = datetime.date.today()
        if data.date:
            try:
                parsed_date = datetime.datetime.strptime(data.date, "%Y-%m-%d").date()
            except ValueError:
                # Try reading in DD-MM-YYYY or other formats
                for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
                    try:
                        parsed_date = datetime.datetime.strptime(data.date, fmt).date()
                        break
                    except ValueError:
                        continue
        
        parsed_time = datetime.datetime.now().time()
        if data.time:
            for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p"):
                try:
                    parsed_time = datetime.datetime.strptime(data.time, fmt).time()
                    break
                except ValueError:
                    continue
        
        # 3. Create Interaction
        interaction = models.Interaction(
            hcp_id=hcp.id,
            interaction_type=data.interaction_type,
            date=parsed_date,
            time=parsed_time,
            attendees=data.attendees,
            topics_discussed=data.topics_discussed,
            observed_sentiment=data.observed_sentiment,
            outcomes=data.outcomes,
            follow_up_actions=data.follow_up_actions,
            ai_summary=f"Logged interaction with {hcp.name} regarding products discussed."
        )
        
        db.add(interaction)
        db.flush() # Flush to get interaction ID for secondary tables
        
        # 4. Bind Products
        if data.products:
            for prod_name in data.products:
                prod = resolve_product(db, prod_name)
                interaction.products.append(prod)
                
        # 5. Bind Materials
        if data.materials:
            for mat_name in data.materials:
                mat = resolve_material(db, mat_name)
                interaction.materials.append(mat)
                
        # 6. Bind Samples & Deduct Stock
        if data.samples:
            for s_info in data.samples:
                sample_name = s_info.get("name")
                qty = int(s_info.get("quantity", 1))
                if qty <= 0:
                    continue
                
                sample = resolve_sample(db, sample_name)
                
                # Check stock levels (PREVENT NEGATIVE STOCK)
                if sample.stock_quantity < qty:
                    raise ValueError(
                        f"Insufficient stock for sample '{sample.name}'. "
                        f"Requested: {qty}, Available: {sample.stock_quantity}."
                    )
                
                # Deduct stock
                sample.stock_quantity -= qty
                
                # Add association
                assoc = models.InteractionSample(
                    interaction_id=interaction.id,
                    sample_id=sample.id,
                    quantity=qty
                )
                db.add(assoc)
        
        # 7. Create any follow-ups automatically if follow_up_actions specified
        if data.follow_up_actions:
            follow_up = models.FollowUp(
                interaction_id=interaction.id,
                description=data.follow_up_actions,
                due_date=parsed_date + datetime.timedelta(days=7), # Default: 1 week due date
                status="Pending"
            )
            db.add(follow_up)
            
        db.commit()
        db.refresh(interaction)
        return interaction
        
    except Exception as e:
        db.rollback()
        raise e


def edit_interaction_transactional(db: Session, data: schemas.EditInteractionInput) -> models.Interaction:
    """
    Modifies an existing interaction using a whitelisted set of fields.
    Updates are transactional.
    """
    try:
        # Find interaction
        interaction = None
        if data.interaction_id:
            interaction = db.query(models.Interaction).filter(models.Interaction.id == data.interaction_id).first()
        elif data.hcp_name:
            # Fall back to finding the last interaction for this HCP
            hcp = resolve_hcp(db, data.hcp_name)
            interaction = db.query(models.Interaction).filter(
                models.Interaction.hcp_id == hcp.id
            ).order_by(models.Interaction.date.desc(), models.Interaction.time.desc()).first()
        else:
            # Fall back to the absolute last logged interaction
            interaction = db.query(models.Interaction).order_by(
                models.Interaction.created_at.desc()
            ).first()
            
        if not interaction:
            raise ValueError("No active or previous interaction could be found to modify.")
            
        # Whitelisted fields update
        whitelisted_updates = {}
        
        if data.observed_sentiment is not None:
            sentiment = data.observed_sentiment.strip()
            if sentiment not in ("Positive", "Neutral", "Negative"):
                raise ValueError("observed_sentiment must be one of: Positive, Neutral, Negative")
            whitelisted_updates["observed_sentiment"] = sentiment
            
        if data.topics_discussed is not None:
            whitelisted_updates["topics_discussed"] = data.topics_discussed
            
        if data.interaction_type is not None:
            type_str = data.interaction_type.strip()
            if type_str not in ("Meeting", "Call", "Email", "Video"):
                raise ValueError("interaction_type must be one of: Meeting, Call, Email, Video")
            whitelisted_updates["interaction_type"] = type_str
            
        if data.outcomes is not None:
            whitelisted_updates["outcomes"] = data.outcomes
            
        if data.follow_up_actions is not None:
            whitelisted_updates["follow_up_actions"] = data.follow_up_actions
            
        if data.date is not None:
            try:
                parsed_date = datetime.datetime.strptime(data.date, "%Y-%m-%d").date()
                whitelisted_updates["date"] = parsed_date
            except ValueError:
                # Try other formats
                for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
                    try:
                        whitelisted_updates["date"] = datetime.datetime.strptime(data.date, fmt).date()
                        break
                    except ValueError:
                        continue
                        
        if data.time is not None:
            for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p"):
                try:
                    whitelisted_updates["time"] = datetime.datetime.strptime(data.time, fmt).time()
                    break
                except ValueError:
                    continue

        # Apply whitelisted updates to database object
        for field, val in whitelisted_updates.items():
            setattr(interaction, field, val)
            
        # Update associated FollowUp if follow_up_actions was modified
        if "follow_up_actions" in whitelisted_updates:
            # Check if there is an existing follow_up
            f_up = db.query(models.FollowUp).filter(models.FollowUp.interaction_id == interaction.id).first()
            if f_up:
                f_up.description = whitelisted_updates["follow_up_actions"]
            else:
                f_up = models.FollowUp(
                    interaction_id=interaction.id,
                    description=whitelisted_updates["follow_up_actions"],
                    due_date=interaction.date + datetime.timedelta(days=7),
                    status="Pending"
                )
                db.add(f_up)
                
        db.commit()
        db.refresh(interaction)
        return interaction
        
    except Exception as e:
        db.rollback()
        raise e


def get_hcp_context(db: Session, hcp_name: str) -> dict:
    """
    Retrieves historical context for an HCP, including profile and last 3 interactions.
    """
    hcp = resolve_hcp(db, hcp_name)
    
    # Get last 3 interactions
    recent_interactions = db.query(models.Interaction).filter(
        models.Interaction.hcp_id == hcp.id
    ).order_by(models.Interaction.date.desc(), models.Interaction.time.desc()).limit(3).all()
    
    # Resolve preferences (commonly discussed products)
    products_discussed = []
    for inter in recent_interactions:
        for p in inter.products:
            products_discussed.append(p.name)
    
    preferred_products = list(set(products_discussed))
    
    # Get pending follow-ups
    pending_tasks = db.query(models.FollowUp).join(models.Interaction).filter(
        models.Interaction.hcp_id == hcp.id,
        models.FollowUp.status == "Pending"
    ).all()
    
    serialized_interactions = []
    for inter in recent_interactions:
        serialized_interactions.append({
            "id": inter.id,
            "date": inter.date.strftime("%Y-%m-%d"),
            "type": inter.interaction_type,
            "topics": inter.topics_discussed,
            "sentiment": inter.observed_sentiment,
            "outcomes": inter.outcomes,
            "follow_up": inter.follow_up_actions
        })
        
    serialized_tasks = []
    for t in pending_tasks:
        serialized_tasks.append({
            "id": t.id,
            "description": t.description,
            "due_date": t.due_date.strftime("%Y-%m-%d") if t.due_date else None,
            "status": t.status
        })

    return {
        "hcp_id": hcp.id,
        "name": hcp.name,
        "specialty": hcp.specialty,
        "clinic_name": hcp.clinic_name,
        "email": hcp.email,
        "phone": hcp.phone,
        "recent_interactions": serialized_interactions,
        "preferred_products": preferred_products,
        "pending_follow_ups": serialized_tasks
    }


def search_interactions(db: Session, query: str = None, limit: int = 5) -> list:
    """
    Searches the history of interactions.
    """
    q = db.query(models.Interaction).join(models.HCP)
    
    if query:
        q = q.filter(
            or_(
                models.HCP.name.ilike(f"%{query}%"),
                models.Interaction.topics_discussed.ilike(f"%{query}%"),
                models.Interaction.outcomes.ilike(f"%{query}%"),
                models.Interaction.follow_up_actions.ilike(f"%{query}%"),
                models.Interaction.observed_sentiment.ilike(f"%{query}%")
            )
        )
        
    results = q.order_by(models.Interaction.date.desc(), models.Interaction.time.desc()).limit(limit).all()
    
    serialized = []
    for inter in results:
        serialized.append({
            "id": inter.id,
            "hcp_name": inter.hcp.name,
            "date": inter.date.strftime("%Y-%m-%d"),
            "time": inter.time.strftime("%H:%M"),
            "interaction_type": inter.interaction_type,
            "topics_discussed": inter.topics_discussed,
            "observed_sentiment": inter.observed_sentiment,
            "outcomes": inter.outcomes,
            "follow_up_actions": inter.follow_up_actions,
            "products": [p.name for p in inter.products],
            "materials": [m.name for m in inter.materials],
            "samples": [{"name": assoc.sample.name, "quantity": assoc.quantity} for assoc in inter.samples_association]
        })
    return serialized


def get_metadata(db: Session) -> dict:
    """
    Fetches lists of all HCPs, Products, Materials, and Samples to populate form elements and options.
    """
    hcps = db.query(models.HCP).all()
    products = db.query(models.Product).all()
    materials = db.query(models.Material).all()
    samples = db.query(models.Sample).all()
    
    return {
        "hcps": hcps,
        "products": products,
        "materials": materials,
        "samples": samples
    }


def manual_create_interaction(db: Session, req: schemas.ManualCreateInteractionRequest) -> models.Interaction:
    """
    Manually creates an interaction from the React form submit.
    """
    try:
        # Verify HCP exists
        hcp = db.query(models.HCP).filter(models.HCP.id == req.hcp_id).first()
        if not hcp:
            raise ValueError(f"HCP ID {req.hcp_id} not found.")
            
        parsed_time = datetime.datetime.strptime(req.time, "%H:%M").time()
        
        interaction = models.Interaction(
            hcp_id=req.hcp_id,
            interaction_type=req.interaction_type,
            date=req.date,
            time=parsed_time,
            attendees=req.attendees,
            topics_discussed=req.topics_discussed,
            observed_sentiment=req.observed_sentiment,
            outcomes=req.outcomes,
            follow_up_actions=req.follow_up_actions,
            ai_summary="Logged manually by representative."
        )
        db.add(interaction)
        db.flush()
        
        # Products
        for p_id in req.products:
            prod = db.query(models.Product).filter(models.Product.id == p_id).first()
            if prod:
                interaction.products.append(prod)
                
        # Materials
        for m_id in req.materials:
            mat = db.query(models.Material).filter(models.Material.id == m_id).first()
            if mat:
                interaction.materials.append(mat)
                
        # Samples
        for s_info in req.samples:
            s_id = int(s_info.get("id"))
            qty = int(s_info.get("quantity", 1))
            if qty <= 0:
                continue
                
            sample = db.query(models.Sample).filter(models.Sample.id == s_id).first()
            if not sample:
                raise ValueError(f"Sample ID {s_id} not found.")
                
            if sample.stock_quantity < qty:
                raise ValueError(
                    f"Insufficient stock for sample '{sample.name}'. "
                    f"Requested: {qty}, Available: {sample.stock_quantity}."
                )
                
            sample.stock_quantity -= qty
            
            assoc = models.InteractionSample(
                interaction_id=interaction.id,
                sample_id=sample.id,
                quantity=qty
            )
            db.add(assoc)
            
        if req.follow_up_actions:
            follow_up = models.FollowUp(
                interaction_id=interaction.id,
                description=req.follow_up_actions,
                due_date=req.date + datetime.timedelta(days=7),
                status="Pending"
            )
            db.add(follow_up)
            
        db.commit()
        db.refresh(interaction)
        return interaction
        
    except Exception as e:
        db.rollback()
        raise e


def manual_edit_interaction(db: Session, interaction_id: int, req: schemas.ManualEditInteractionRequest) -> models.Interaction:
    """
    Manually edits an interaction from the React form submit.
    """
    try:
        interaction = db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
        if not interaction:
            raise ValueError(f"Interaction ID {interaction_id} not found.")
            
        # Update whitelisted fields
        if req.interaction_type is not None:
            interaction.interaction_type = req.interaction_type
        if req.date is not None:
            interaction.date = req.date
        if req.time is not None:
            interaction.time = datetime.datetime.strptime(req.time, "%H:%M").time()
        if req.attendees is not None:
            interaction.attendees = req.attendees
        if req.topics_discussed is not None:
            interaction.topics_discussed = req.topics_discussed
        if req.observed_sentiment is not None:
            interaction.observed_sentiment = req.observed_sentiment
        if req.outcomes is not None:
            interaction.outcomes = req.outcomes
            
        if req.follow_up_actions is not None:
            interaction.follow_up_actions = req.follow_up_actions
            # Sync follow_up
            f_up = db.query(models.FollowUp).filter(models.FollowUp.interaction_id == interaction_id).first()
            if f_up:
                f_up.description = req.follow_up_actions
            else:
                f_up = models.FollowUp(
                    interaction_id=interaction.id,
                    description=req.follow_up_actions,
                    due_date=interaction.date + datetime.timedelta(days=7),
                    status="Pending"
                )
                db.add(f_up)
                
        # Products
        if req.products is not None:
            # Clear old and set new
            interaction.products = []
            for p_id in req.products:
                prod = db.query(models.Product).filter(models.Product.id == p_id).first()
                if prod:
                    interaction.products.append(prod)
                    
        # Materials
        if req.materials is not None:
            interaction.materials = []
            for m_id in req.materials:
                mat = db.query(models.Material).filter(models.Material.id == m_id).first()
                if mat:
                    interaction.materials.append(mat)
                    
        # Samples (Refunding old inventory and deducting new is complex; for a simple assignment edit,
        # we will allow editing text fields conversationally and manually. If manually setting samples is requested,
        # we will handle it by reverting prior samples and applying new, or simply returning a validation error if stock check fails).
        if req.samples is not None:
            # Refund previous samples first
            for assoc in list(interaction.samples_association):
                assoc.sample.stock_quantity += assoc.quantity
                db.delete(assoc)
            
            # Apply new samples
            for s_info in req.samples:
                s_id = int(s_info.get("id"))
                qty = int(s_info.get("quantity", 1))
                if qty <= 0:
                    continue
                    
                sample = db.query(models.Sample).filter(models.Sample.id == s_id).first()
                if not sample:
                    raise ValueError(f"Sample ID {s_id} not found.")
                
                if sample.stock_quantity < qty:
                    raise ValueError(
                        f"Insufficient stock for sample '{sample.name}'. "
                        f"Requested: {qty}, Available: {sample.stock_quantity}."
                    )
                
                sample.stock_quantity -= qty
                assoc = models.InteractionSample(
                    interaction_id=interaction.id,
                    sample_id=sample.id,
                    quantity=qty
                )
                db.add(assoc)
                
        db.commit()
        db.refresh(interaction)
        return interaction
        
    except Exception as e:
        db.rollback()
        raise e
