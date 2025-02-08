import logging
import os


from django.shortcuts import render, get_object_or_404, redirect, HttpResponse
from django.utils.timezone import localtime, make_aware, now
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.conf import settings
from django.db.models import F
from django import forms

from autobidder_app.management.commands.ahrefs_data import AhrefsFetcher
from autobidder_app.management.commands.voodoo_parse import run_parser
from autobidder_app.models import AhrefsData, Domain, Bet
from .utils.ahrefs_balance import check_api_limit

import asyncio
import csv


from datetime import datetime, timedelta
from .forms import BetForm, ClaimBetForm
import re

def run_voodoo_parser(request):
    result = run_parser()
    return JsonResponse(result)


def ahrefs_data_view(request):
    fields = [
        ('domain_rating', 'DR'),
        ('ref_domains', 'Ref Dom'),
        ('backlinks', 'BL'),
        ('dofollow_links', 'DF Links'),
        ('ahrefs_top', 'Top'),
        ('alternate_links', 'Alt Links'),
        ('canonical_links', 'CL'),
        ('gov_links', 'Gov Links'),
        ('edu_links', 'Edu Links'),
        ('external_links', 'Ext Links'),
        ('redirect_links', 'Redirects'),
        ('sponsored_links', 'Spon Links'),
        ('html_pages', 'HTML Pgs'),
        ('image_links', 'Img Links'),
        ('internal_links', 'Int Links'),
        ('linked_root_domains', 'LRD'),
        ('nofollow_links', 'NF Links'),
        ('pages', 'Pgs'),
        ('ref_class_c', 'Ref C-Class'),
        ('ref_ips', 'Ref IPs'),
        ('ref_pages', 'Ref Pgs'),
        ('rss_links', 'RSS Links'),
        ('text_links', 'Txt Links'),
        ('ugc_links', 'UGC Links'),
        ('valid_pages', 'Valid Pgs'),
    ]

    tomorrow = localtime(now()).date() + timedelta(days=1)
    start_date_str = request.GET.get('start_date', tomorrow.isoformat())
    end_date_str = request.GET.get('end_date', tomorrow.isoformat())

    start_date = make_aware(datetime.strptime(start_date_str, "%Y-%m-%d"))
    end_date = make_aware(datetime.strptime(end_date_str, "%Y-%m-%d")) + timedelta(days=1) - timedelta(seconds=1)

    # Визначення сортування
    sort_field = request.GET.get('sort', 'domain__expiration_date')
    sort_order = request.GET.get('order', 'asc')

    valid_fields = [field[0] for field in fields] + ['domain__expiration_date']
    if sort_field not in valid_fields:
        sort_field = 'domain__expiration_date'

    order_by = F(sort_field).asc() if sort_order == 'asc' else F(sort_field).desc()

    # Отримання даних AhrefsData
    ahrefs_data = AhrefsData.objects.select_related('domain').filter(
        domain__expiration_date__range=[start_date, end_date]
    ).order_by(order_by).values(
        'domain__domain_id',
        'domain__name',
        'domain__expiration_date',
        *[field[0] for field in fields]
    )

    formatted_data = [
        {
            'domain_id': entry.get('domain__domain_id', 'N/A'),
            'expiration_date': localtime(entry.get('domain__expiration_date')).strftime('%Y-%m-%d %H:%M')
            if entry.get('domain__expiration_date') else 'N/A',
            'domain': entry.get('domain__name', 'Unknown'),
            'max_bet': 'N/A',
            **{field[0]: entry.get(field[0], 'N/A') for field in fields}
        }
        for entry in ahrefs_data
    ]

    form = ClaimBetForm()

    context = {
        'fields': fields,
        'ahrefs_data': formatted_data,
        'sort_field': sort_field,
        'sort_order': sort_order,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'form': form,
    }
    return render(request, 'ahrefs_data.html', context)


logger = logging.getLogger(__name__)


def claim_bet(request):
    if request.method == "POST":
        try:
            domain_id = request.POST.get('domain_id')
            expiration_date = request.POST.get('expiration_date')
            max_bet = request.POST.get('max_bet')

            if not domain_id or not max_bet:
                logger.error("Missing domain_id or max_bet")
                return JsonResponse({"status": "error", "message": "Missing domain_id or max_bet"}, status=400)

            expiration_date_obj = make_aware(datetime.strptime(expiration_date, "%Y-%m-%d %H:%M"))
            domain = Domain.objects.get(domain_id=domain_id)

            Bet.objects.update_or_create(
                domain=domain,
                defaults={'expiration_date': expiration_date_obj, 'max_bet': max_bet}
            )

            return JsonResponse({"status": "success", "message": "Bet saved successfully!"})
        except Exception as e:
            logger.error(f"Error processing bet: {str(e)}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)


def all_bets_view(request):
    bets = Bet.objects.select_related('domain').order_by('-created_at')
    bets_with_forms = [(bet, BetForm(instance=bet)) for bet in bets]

    return render(request, 'all_bets.html', {
        'bets_with_forms': bets_with_forms
    })
# I know this is not safe, but it works for my private prject
@csrf_exempt
def update_max_bet(request, bet_id):
    bet = get_object_or_404(Bet, domain_id=bet_id)
    if request.method == 'POST':
        form = BetForm(request.POST, instance=bet)
        if form.is_valid():
            form.save()
            return redirect('all_bets')
    return redirect('all_bets')

@csrf_exempt
def delete_bet(request, bet_id):
    bet = get_object_or_404(Bet, domain_id=bet_id)
    bet.delete()
    return redirect('all_bets')

LOGS_DIR = os.path.join(settings.BASE_DIR, 'logs/make_bets')


def parse_log_entry(file_name, line):   #
    timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
    match = re.search(timestamp_pattern, line)
    if match:
        timestamp = datetime.strptime(match.group(0), '%Y-%m-%d %H:%M:%S')
    else:
        timestamp = datetime.now() #to see when the error occured for debugging

    return timestamp, f"{file_name}: {line.strip()}"


def log_list_view(request):
    """Shows the logs on page"""
    log_entries = []
    query = request.GET.get('q', '').strip().lower()

    if os.path.exists(LOGS_DIR):
        # Get files sorted newest first
        log_files = sorted(os.listdir(LOGS_DIR), reverse=True)

        for log_file in log_files:
            file_path = os.path.join(LOGS_DIR, log_file)
            with open(file_path, 'r') as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if query in line.lower():
                        log_entries.append(parse_log_entry(log_file, line))

    log_entries.sort(key=lambda x: x[0], reverse=True)

    paginator = Paginator([entry[1] for entry in log_entries], 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'logs_list.html', {
        'page_obj': page_obj,
        'query': query
    })



########################################################################
# test functionality, not ready yet

class AhrefsForm(forms.Form):
    domains = forms.CharField(
        label="Enter Domains (one per line)",
        widget=forms.Textarea(attrs={"rows": 5, "class": "form-control"}),
    )


async def fetch_ahrefs_bulk(domains):
    fetcher = AhrefsFetcher()
    results = await fetcher.fetch_all(domains)

    for i, domain in enumerate(domains):
        if i < len(results):
            results[i]['domain'] = domain

    return results


def ahrefs_test_view(request):
    results = None
    form = AhrefsForm()
    api_balance = check_api_limit()
    all_fields = []

    if request.method == "POST":
        form = AhrefsForm(request.POST)
        if form.is_valid():
            domain_list = form.cleaned_data["domains"].splitlines()
            domain_list = [d.strip() for d in domain_list if d.strip()]

            if domain_list:
                results = asyncio.run(fetch_ahrefs_bulk(domain_list))
                request.session["ahrefs_results"] = results

                all_fields = list({key for data in results if data for key in data.keys()})

    return render(request, "ahrefs_test.html", {
        "form": form,
        "results": results,
        "api_balance": api_balance,
        "fields": all_fields
    })



def download_ahrefs_data(request, file_type):
    results = request.session.get("ahrefs_results", [])

    if not results:
        return HttpResponse("No data available to download.", content_type="text/plain")

    if file_type == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="ahrefs_data.csv"'

        writer = csv.writer(response)
        writer.writerow(["Domain", "Domain Rating", "Ahrefs Top", "Backlinks", "Ref Pages",
                         "Ref Domains", "External Links", "Internal Links", "Text Links", "Image Links",
                         "Dofollow Links", "Nofollow Links", "Redirect Links", "Canonical Links",
                         "Gov Links", "Edu Links", "RSS Links", "Alternate Links", "HTML Pages",
                         "Ref Class C", "Ref IPs", "Linked Root Domains"])

        for data in results:
            if data:
                writer.writerow([
                    data.get("domain", ""),
                    data.get("domain_rating", ""),
                    data.get("ahrefs_top", ""),
                    data.get("backlinks", ""),
                    data.get("ref_pages", ""),
                    data.get("ref_domains", ""),
                    data.get("external_links", ""),
                    data.get("internal_links", ""),
                    data.get("text_links", ""),
                    data.get("image_links", ""),
                    data.get("dofollow_links", ""),
                    data.get("nofollow_links", ""),
                    data.get("redirect_links", ""),
                    data.get("canonical_links", ""),
                    data.get("gov_links", ""),
                    data.get("edu_links", ""),
                    data.get("rss_links", ""),
                    data.get("alternate_links", ""),
                    data.get("html_pages", ""),
                    data.get("ref_class_c", ""),
                    data.get("ref_ips", ""),
                    data.get("linked_root_domains", ""),
                ])
        return response

    return HttpResponse("Invalid file type.", content_type="text/plain")