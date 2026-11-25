from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..interview.engine import missing_fields
from ..models import Pack as PackRow
from ..models import Profile, User
from ..packs.loader import PackError, _cache, get_pack, parse_pack
from ..packs.schema import Pack
from ..schemas import PackDetail, PackSummary, PackUpload, ProfileFieldOut, ProfileIn, ProfileOut
from ..security import current_user, require_role

router = APIRouter(prefix="/api", tags=["packs"])


def summary(p: Pack, row: PackRow) -> PackSummary:
    return PackSummary(
        slug=p.id,
        name=p.name,
        category=p.category,
        description=p.description.strip(),
        session_length=p.session_length,
        question_count=len(p.questions),
        builtin=row.builtin,
        active=row.active,
    )


@router.get("/packs", response_model=list[PackSummary])
async def list_packs(db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    rows = (await db.scalars(select(PackRow).order_by(PackRow.builtin.desc(), PackRow.name))).all()
    return [summary(parse_pack(r.source_yaml), r) for r in rows if r.active or user.role == "admin"]


@router.get("/packs/{slug}", response_model=PackDetail)
async def pack_detail(slug: str, db: AsyncSession = Depends(get_db), _: User = Depends(current_user)):
    row = await db.scalar(select(PackRow).where(PackRow.slug == slug))
    pack = await get_pack(db, slug)
    if not pack or not row:
        raise HTTPException(404, "Interview type not found")
    return PackDetail(
        **summary(pack, row).model_dump(),
        persona=pack.persona.strip(),
        honesty_note=pack.honesty_note,
        profile_fields=[ProfileFieldOut(**f.model_dump(exclude={"entity"})) for f in pack.profile_fields],
        rubric=pack.rubric,
    )


@router.post("/packs", response_model=PackSummary, status_code=201)
async def upload_pack(body: PackUpload, db: AsyncSession = Depends(get_db), _: User = Depends(require_role("admin"))):
    try:
        pack = parse_pack(body.yaml)
    except PackError as e:
        raise HTTPException(422, str(e)) from e
    row = await db.scalar(select(PackRow).where(PackRow.slug == pack.id))
    if row and row.builtin:
        raise HTTPException(409, "Built-in packs can't be overwritten; use a new id")
    if row:
        row.name, row.source_yaml, row.version = pack.name, body.yaml, row.version + 1
    else:
        row = PackRow(slug=pack.id, name=pack.name, version=pack.version, source_yaml=body.yaml, builtin=False)
        db.add(row)
    await db.commit()
    _cache.clear()
    return summary(pack, row)


@router.patch("/packs/{slug}/active", response_model=PackSummary)
async def toggle_pack(slug: str, active: bool, db: AsyncSession = Depends(get_db), _: User = Depends(require_role("admin"))):
    row = await db.scalar(select(PackRow).where(PackRow.slug == slug))
    if not row:
        raise HTTPException(404, "Interview type not found")
    row.active = active
    await db.commit()
    return summary(parse_pack(row.source_yaml), row)


# --- profiles ------------------------------------------------------------------------------
def clean_profile(pack: Pack, data: dict) -> dict:
    out = {}
    for f in pack.profile_fields:
        v = data.get(f.id)
        if v is None:
            continue
        if f.type == "list":
            items = v if isinstance(v, list) else str(v).splitlines()
            v = [str(i).strip()[:200] for i in items if str(i).strip()][:10]
        elif f.type == "number":
            try:
                v = float(str(v).replace(",", "")) if str(v).strip() else None
            except ValueError:
                raise HTTPException(422, f"{f.label} must be a number") from None
            if v is not None and v.is_integer():
                v = int(v)
        else:
            v = str(v).strip()[:2000]
            if f.type == "select" and f.options and v and v not in f.options:
                raise HTTPException(422, f"{f.label} must be one of {f.options}")
        out[f.id] = v
    return out


@router.get("/profiles/{slug}", response_model=ProfileOut)
async def get_profile(slug: str, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    pack = await get_pack(db, slug)
    if not pack:
        raise HTTPException(404, "Interview type not found")
    row = await db.scalar(select(Profile).where(Profile.user_id == user.id, Profile.pack_slug == slug))
    data = row.data if row else {}
    return ProfileOut(pack_slug=slug, data=data, missing=missing_fields(pack, data))


@router.put("/profiles/{slug}", response_model=ProfileOut)
async def put_profile(slug: str, body: ProfileIn, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)):
    pack = await get_pack(db, slug)
    if not pack:
        raise HTTPException(404, "Interview type not found")
    data = clean_profile(pack, body.data)
    row = await db.scalar(select(Profile).where(Profile.user_id == user.id, Profile.pack_slug == slug))
    if row:
        row.data = data
    else:
        db.add(Profile(user_id=user.id, pack_slug=slug, data=data))
    await db.commit()
    return ProfileOut(pack_slug=slug, data=data, missing=missing_fields(pack, data))
