---
repo: architecture
path: docs/architecture/aw-marketplace.md
source: generated
edited: false
checksum: sha256:902285f0ab0afbd8b51792c2959831ed31eb996337844f9a15a31cdef529667a
---
# aw-marketplace

- **repo**: aw-marketplace
- **layer**: infrastructure
- **technologies**: python
- **health** (derived): planned

The apps marketplace catalog — a single apps.json listing every app installable from the aw-workspace "Marketplace" screen (Apps view → Marketplace button). JSON (not YAML) keeps field names consistent with each app's own aw-app.json manifest. This repo is the distribution source for workspace apps; the install runtime lives in aw-workspace.

## Connections
_none_

## MCP tools
_none exposed_

## Requirements
### A primeira release de um aw-app-* novo cria sua própria entrada no catálogo
- Given um repo aw-app-* acabou de sair e o apps.json do marketplace ainda não tem nenhuma linha com aquele id
- When o sync roda contra o catálogo (repos/aw-marketplace/scripts/sync_catalog_entry.py::apply_to_catalog:81, que ao não achar o id chama ::create_entry:33)
- Then uma entrada conservadora é acrescentada — icon "plug", category "dev-tools", has_config derivado de config_schema.properties e bootstrap de contributes.system_clis — e o PR de sync abre sozinho. Sem esse caminho, o app novo simplesmente não aparece: o workflow de release termina verde, nenhum PR é aberto e ninguém descobre que o app não está no catálogo até tentar instalá-lo
- intended_status: `not_implemented` · derived health: `not_implemented`
- tests: `repos/aw-marketplace/tests/test_sync_catalog_entry.py` (passing)

### PR de sync superseded fecha sozinho, e o que ainda está à frente do master fica de pé
- Given duas releases do mesmo app abriram dois PRs sync/<app> e o mais novo mergeou primeiro, deixando o outro com uma versão que o master já ultrapassou
- When a varredura compara a versão do apps.json de cada branch com a do master (repos/aw-marketplace/scripts/close_stale_syncs.py::close_stale_syncs:65, decisão em :96)
- Then só os PRs com master_version >= pr_version são comentados e fechados; um PR ainda à frente (0.10.0 contra 0.9.0 no master) fica intocado, branches fora do padrão sync/* são ignoradas, e um commit que sumiu no meio da execução é pulado em vez de derrubar a rodada. Fechar por data ou por "existe um mais novo" mataria o PR que ainda tinha a versão boa, e a release ficaria para trás no catálogo sem nada indicando que foi o próprio bot que a descartou
- intended_status: `not_implemented` · derived health: `not_implemented`
- tests: `repos/aw-marketplace/tests/test_close_stale_syncs.py` (passing)

### Patch só quando TODO commit é fix/docs/chore; major só quando alguém pede
- Given a release lê os assuntos dos commits desde a última tag, e nem todo commit deste ecossistema segue conventional commits
- When o bump é decidido (repos/aw-marketplace/scripts/bump_version.py::determine_bump:16, aplicado por ::bump_semver:33)
- Then o bump manual "major" vence tudo, patch sai apenas se todos os assuntos casarem com os prefixos de patch, e qualquer commit não convencional na mistura — ou nenhum commit — cai em minor. O default tem que ser o lado seguro: um commit sem prefixo classificado como patch entrega mudança de comportamento num número que diz "só correção", e quem atualiza confiando no semver não olha o diff. bump_semver ainda recusa qualquer coisa que não seja X.Y.Z, em vez de propagar uma versão inventada para o catálogo
- intended_status: `not_implemented` · derived health: `not_implemented`
- tests: `repos/aw-marketplace/tests/test_bump_version.py` (passing)

### O schema mora aqui mesmo quando o catálogo validado é de outro repo
- Given um app privado sincroniza para tekflox/aw-marketplace-private, que carrega só um apps.json e nenhum schema — o catalog_repo do app-release.yml
- When a validação recebe o caminho do catálogo alvo (repos/aw-marketplace/tests/validate_apps.py::main:23)
- Then o catálogo externo é validado contra o schema DESTE repo, uma violação de schema ou ids duplicados falham com mensagem nomeando o arquivo (:39), um catálogo inexistente retorna 1 em vez de estourar traceback, e mais de um caminho é erro de uso (2). Sem o argumento de caminho o CI do repo privado validaria o catálogo errado — o daqui — e passaria verde sobre um apps.json que nunca foi olhado
- intended_status: `not_implemented` · derived health: `not_implemented`
- tests: `repos/aw-marketplace/tests/test_validate_apps.py` (passing)
