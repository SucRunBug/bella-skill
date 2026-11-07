#!/usr/bin/env python3
"""Validate a reviewed Bot content pack and zip only declared deliverables.

No network, image generation, confirmation mutation, or spreadsheet authoring.
"""
import argparse
import datetime
import json
import math
import struct
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile, ZIP_DEFLATED


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_file(root, relative):
    require(isinstance(relative, str) and relative.strip(), 'Missing file path')
    p = Path(relative)
    require(not p.is_absolute(), 'Deliverable paths must be relative')
    target = (root / p).resolve()
    require(target.is_relative_to(root), 'Deliverable escapes task directory')
    require(target.is_file() and target.stat().st_size > 0,
            'Missing or empty file: ' + relative)
    return target


def web_url(value):
    parsed = urlparse(value) if isinstance(value, str) else None
    return bool(parsed and parsed.scheme in ('http', 'https') and parsed.netloc)


def check_image(path):
    with path.open('rb') as f:
        header = f.read(32)
    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        require(len(header) >= 24 and header[12:16] == b'IHDR', 'Invalid PNG')
        width, height = struct.unpack('>II', header[16:24])
        require(width > 0 and height > 0 and abs(width / height - .75) <= .035,
                'Expected 3:4 portrait: ' + path.name)
    else:
        require(header.startswith(b'\xff\xd8\xff') or
                (header.startswith(b'RIFF') and header[8:12] == b'WEBP'),
                'Unsupported or invalid raster: ' + path.name)


def validate(manifest, plan_only=False):
    manifest = Path(manifest).resolve()
    root = manifest.parent
    data = json.loads(manifest.read_text(encoding='utf-8'))
    for key in ('topic', 'plan_version', 'title', 'cover_question', 'caption',
                'first_comment', 'viral_logic', 'seasonal_hook'):
        require(bool(data.get(key)), 'Missing content field: ' + key)
    datetime.date.fromisoformat(data['publish_date'])
    require(data.get('stage') in ('proposal', 'approved', 'complete'), 'Invalid stage')
    require(data.get('mode') in ('products', 'editorial'), 'Invalid mode')
    titles = data.get('title_candidates', [])
    require(len(titles) == 5 and len(set(titles)) == 5 and data['title'] in titles,
            'Provide five distinct title candidates including the recommendation')
    limit = data.get('constraints', {}).get('title_max_chars', 20)
    require(isinstance(limit, int) and limit > 0, 'Invalid title length limit')
    require(all(isinstance(t, str) and 0 < len(t) <= limit for t in titles),
            'Title exceeds configured length')
    tags = data.get('tags', [])
    require(6 <= len(tags) <= 10 and all(isinstance(t, str) and t for t in tags),
            'Provide 6 to 10 topic tags')
    visual = data.get('visual', {})
    for key in ('palette', 'layout', 'typography', 'ip', 'decorations'):
        require(bool(visual.get(key)), 'Missing visual specification: ' + key)
    count, per_page = data.get('item_count', 9), data.get('per_page', 3)
    require(isinstance(count, int) and count > 0 and isinstance(per_page, int)
            and per_page > 0, 'Invalid item or page size')
    items = data.get('items', [])
    require(len(items) == count, 'Item count mismatch')
    ids = [x.get('id') for x in items]
    require(all(ids) and len(set(ids)) == count, 'Item IDs missing or duplicated')
    page_count = math.ceil(count / per_page)
    for page in range(1, page_count + 1):
        expected = min(per_page, count - (page - 1) * per_page)
        require(sum(x.get('page') == page for x in items) == expected,
                'Item allocation mismatch on page ' + str(page))
    files = data.get('files', {})
    paths = [manifest]
    for key in ('plan', 'copy'):
        paths.append(local_file(root, files.get(key)))
    if plan_only:
        return data, list(dict.fromkeys(paths))
    require(data.get('stage') == 'complete', 'Pack is not complete')
    approval = data.get('approval', {})
    require(approval.get('confirmed') is True, 'Visual plan has not been confirmed')
    require(approval.get('plan_version') == data['plan_version'],
            'Confirmation belongs to a different plan version')
    require(bool(approval.get('user_confirmation')), 'Missing user confirmation record')
    budget = data.get('constraints', {}).get('unit_budget')
    for item in items:
        require(item.get('name'), 'Missing item name')
        sources = item.get('source_urls', [])
        require(sources and all(web_url(u) for u in sources), 'Missing source URLs')
        if data['mode'] == 'products':
            require(item.get('spec') and web_url(item.get('buy_url')),
                    'Missing product specification or purchase/source URL')
            if budget is not None:
                price = item.get('price')
                require(isinstance(price, (int, float)) and not isinstance(price, bool)
                        and math.isfinite(price) and 0 <= price <= budget,
                        'Unknown or over-budget product price')
                require(item.get('price_basis') == 'single_purchasable_unit',
                        'Budget price is not an independently purchasable unit')
    for key in ('prompts', 'sources', 'research'):
        paths.append(local_file(root, files.get(key)))
    # Workbook, original product photos, IP references and other deliverables
    # are opt-in through the manifest, with the same task-directory boundary.
    # Do not silently omit a declared file from the complete archive.
    for name in files.values():
        paths.append(local_file(root, name))
    images = data.get('images', {})
    interiors = images.get('interiors', [])
    require(len(interiors) == page_count, 'Interior image count mismatch')
    image_names = [images.get('cover')] + interiors
    require(len(set(image_names)) == page_count + 1, 'Image paths must be distinct')
    for name in image_names:
        path = local_file(root, name)
        check_image(path)
        paths.append(path)
    return data, list(dict.fromkeys(paths))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['validate-plan', 'validate', 'package'])
    parser.add_argument('manifest')
    parser.add_argument('--output')
    args = parser.parse_args()
    try:
        data, paths = validate(args.manifest, args.command == 'validate-plan')
        result = {'status': 'ok', 'stage': data['stage'], 'topic': data['topic'],
                  'items': len(data['items']), 'files_checked': len(paths)}
        if args.command == 'package':
            require(args.output, 'package requires --output')
            target = Path(args.output).resolve()
            require(target.suffix.lower() == '.zip', 'Output must be a zip file')
            require(target not in paths, 'Cannot replace an input deliverable')
            target.parent.mkdir(parents=True, exist_ok=True)
            root = Path(args.manifest).resolve().parent
            with ZipFile(target, 'w', ZIP_DEFLATED) as z:
                for path in paths:
                    z.write(path, path.relative_to(root).as_posix())
            with ZipFile(target) as z:
                require(z.testzip() is None, 'Zip integrity check failed')
            result['output'] = str(target)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
