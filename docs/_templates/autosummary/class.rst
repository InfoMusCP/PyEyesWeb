{{ fullname | escape | underline }}

.. currentmodule:: {{ module }}

{# Members of the class itself only: the inherited ones (int methods of Status, dict methods, ...) are not part of the
   documented API. Every member of the tables is documented below them by :members:, so each entry of a table resolves
   (nitpicky, DOCS_PLAN 11.2). #}
{%- set own_methods = methods | reject("in", inherited_members) | reject("equalto", "__init__") | list %}
{%- set own_attributes = attributes | reject("in", inherited_members) | list %}

.. autoclass:: {{ objname }}
{%- if own_methods or own_attributes %}
   :members: {{ (own_methods + own_attributes) | join(", ") }}
   :undoc-members:
{%- endif %}

{% if own_methods %}
   .. rubric:: Methods

   .. autosummary::
{% for item in own_methods %}
      ~{{ name }}.{{ item }}
{%- endfor %}
{% endif %}
{% if own_attributes %}
   .. rubric:: Attributes

   .. autosummary::
{% for item in own_attributes %}
      ~{{ name }}.{{ item }}
{%- endfor %}
{% endif %}
