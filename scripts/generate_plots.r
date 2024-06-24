library(VennDiagram)
library(RColorBrewer)
library(ggplot2)
library(tidyr)
library(dplyr)
library(xtable)

load_data <- function() {
  df_old <- read.csv('results_file.csv', header = TRUE)
  return(df_old);
}

clean_data <- function (df_old) {
  df <- data.frame(matrix(ncol = 7, nrow = 0))
  for (i in 1:nrow(df_old)) {
    dimensions <- paste(df_old[i, 'width'], df_old[i, 'height'], sep="x")
    name <- paste(df_old[i, 'algorithm'], "-", dimensions, "-", df_old[i, 'genSeed'], "-",
                  df_old[i, 'cyclePercentage'], "-", df_old[i, 'method'], sep="")
    df <-
        rbind(df,
              c( df_old[i, 'tool']     # tool
               , name                  # name
               , dimensions            # dimensions
               , df_old[i, 'fuzzSeed'] # seed
               , df_old[i, 'bugFound'] # bug_found
               , df_old[i, 'crash']    # crash
               , df_old[i, 'timeMs']   # time in ms
               ))
  }
  colnames(df) <-
    c('tool', 'name', 'size', 'seed', 'bugFound', 'crash', 'timeMs')
  df$timeMs <- as.numeric(df$timeMs)
  df$seed <- as.numeric(df$seed)
  df$bugFound <- as.numeric(df$bugFound)
  df$crash <- ifelse(df$crash=="1",TRUE,FALSE)
  return(df)
}

found_bug_bar_plots <- function(df) {
  df_bugs_found <- df %>%
    group_by(size, tool) %>%
    summarise(nBugsFound = sum(bugFound))

  df_bugs_found$size <- factor(
    df_bugs_found$size,
    levels = c('5x5','10x10', '15x15', '20x20')
  )

  df_bugs_found$tool <- factor(
    df_bugs_found$tool,
    levels = c('ityfuzz', 'echidna', 'medusa', 'foundry')
  )

  ggplot(df_bugs_found, aes(x = tool, y = nBugsFound, fill = size)) +
    geom_bar(width = 0.5,
             stat = "identity",
             position = position_dodge(0.8)) +
    labs(x = "Fuzzer",
         y = "Number of solved mazes",
         fill = "Maze Dimensions") +
    scale_fill_discrete(breaks=c('20x20', '15x15', '10x10', '5x5')) +
    theme(axis.text.y = element_text(size = 12)) +
    theme(axis.text.x = element_text(size = 12)) +
    theme(aspect.ratio=1) +
    coord_flip()
}

time_bug_cactus_plots <- function(df) {
  df_cumsum <- df %>%
    group_by(tool) %>% 
    filter(bugFound > 0 & crash == FALSE) %>%
    arrange(timeMs, .by_group = TRUE) %>%
    mutate(counter = row_number(), cum_sum = cumsum(timeMs), cum_sum_m = cum_sum / 60000)

  df_cumsum$tool <- factor(
    df_cumsum$tool,
    levels = c('foundry', 'medusa', 'echidna', 'ityfuzz')
  )

  # divide milliseconds by 60000 to get minutes
  ggplot(df_cumsum, aes(x = counter, y = timeMs / 60000, color = tool)) +
    geom_line() +
    labs(x = "Number of solved mazes",
         y = "Time to solve in minutes",
         color = "Fuzzer") +
    scale_shape_manual(values = c(2, 3, 4, 6, 0, 5, 7)) +
    guides(shape = "none") +
    theme(aspect.ratio=1)
}

venn_dia_plots <- function(df) {

  df_tools <- df %>%
    filter(bugFound > 0 & crash == FALSE) %>%
    select(tool, name)

  foundry_bm <- (df_tools %>% filter(tool == 'foundry'))$name
  medusa_bm  <- (df_tools %>% filter(tool == 'medusa'))$name
  echidna_bm <- (df_tools %>% filter(tool == 'echidna'))$name
  ityfuzz_bm <- (df_tools %>% filter(tool == 'ityfuzz'))$name

  max_ln <- max(length(foundry_bm), length(medusa_bm),
    length(echidna_bm), length(ityfuzz_bm))

  foundry_bm <- c(foundry_bm, rep(NA, max_ln - length(foundry_bm)))
  medusa_bm  <- c(medusa_bm,  rep(NA, max_ln - length(medusa_bm)))
  echidna_bm <- c(echidna_bm, rep(NA, max_ln - length(echidna_bm)))
  ityfuzz_bm <- c(ityfuzz_bm, rep(NA, max_ln - length(ityfuzz_bm)))

  venn.diagram(
    x = list(
       foundry_bm,
       medusa_bm,
       echidna_bm,
       ityfuzz_bm
      ),
    category.names = c("foundry" , "medusa" , "echidna", "ityfuzz"),
    filename = 'venn.tiff',
    disable.logging = TRUE,
    output = TRUE,
    imagetype="tiff",
    col=c("#F8766D55", '#7CAE0055', '#00BFC455', '#C77CFF55'),
    fill=c(
      alpha("#F8766DFF",0.3),
      alpha('#7CAE00FF',0.3),
      alpha('#00BFC4FF',0.3),
      alpha('#C77CFFFF',0.3)
      ),
    fontfamily = "sans",
    cat.fontfamily = "sans",
    na = "remove"
  )
}

df_raw <- load_data()
df <- clean_data(df_raw)

venn_dia_plots(df)
found_bug_bar_plots(df)
time_bug_cactus_plots(df)
