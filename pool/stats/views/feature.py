from django.shortcuts import redirect, render, reverse

from str2bool import str2bool


feature_names = [
    'elo'
]

def index(request):

    features = dict()
    for feature_name in feature_names:
        if feature_name not in request.session:
            request.session[feature_name] = False
            request.session.save()
        features[feature_name] = request.session[feature_name]

    context = {
        'features': features,
    }

    return render(request, 'stats/feature.html', context)


def save(request, feature, setting):

    if feature in feature_names:
        request.session[feature] = str2bool(setting)
        request.session.save()

    return redirect(reverse('feature'))