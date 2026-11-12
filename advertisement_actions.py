"""Atomic actions on property-list state shared by local and hosted backends."""
import cloud_store


def exclude_advertisements(path, keys, *, preserve_favorites=False):
    targets = {str(key) for key in keys if key}
    if not targets:
        return 0
    count = 0

    def update(state):
        nonlocal count
        favorites = set(state.get('favoritos', []))
        excluded = set(state.get('excluidos', []))
        selected = targets - excluded
        if preserve_favorites:
            selected -= favorites
        count = len(selected)
        return {
            **state,
            'favoritos': sorted(favorites - selected),
            'excluidos': sorted(excluded | selected),
            'novos': sorted(set(state.get('novos', [])) - selected),
        }

    cloud_store.update_json(path, {}, update)
    return count
